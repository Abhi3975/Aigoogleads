'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm, type UseFormRegister } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { useOnboarding, useSaveOnboarding } from '@/hooks/use-campaigns';
import { useCurrentOrg } from '@/hooks/use-organizations';
import type { MarketingGoal, OnboardingPayload } from '@/lib/types';
import { cn } from '@/lib/utils';

const GOALS: { value: MarketingGoal; label: string; hint: string }[] = [
  { value: 'generate_leads', label: 'Generate leads', hint: 'Capture enquiries & sign-ups' },
  { value: 'increase_sales', label: 'Increase sales', hint: 'Drive online purchases' },
  { value: 'website_traffic', label: 'Website traffic', hint: 'Grow qualified visits' },
  { value: 'app_installs', label: 'App installs', hint: 'Acquire app users' },
  { value: 'brand_awareness', label: 'Brand awareness', hint: 'Maximise reach' },
  { value: 'local_store_visits', label: 'Local store visits', hint: 'Drive foot traffic' },
];

const schema = z.object({
  business_name: z.string().min(1, 'Required'),
  description: z.string().min(10, 'Add a bit more detail'),
  industry: z.string().min(1, 'Required'),
  website_url: z.string().optional(),
  product_service_description: z.string().optional(),
  usp: z.string().optional(),
  location: z.string().optional(),
  goal: z.enum([
    'generate_leads',
    'increase_sales',
    'website_traffic',
    'app_installs',
    'brand_awareness',
    'local_store_visits',
  ]),
  target_countries: z.string().optional(),
  target_cities: z.string().optional(),
  languages: z.string().optional(),
  daily_budget: z.coerce.number().positive('Must be > 0'),
  monthly_budget: z.coerce.number().positive('Must be > 0'),
  currency: z.string().min(3).max(3),
  max_cpa: z.coerce.number().optional(),
  target_roas: z.coerce.number().optional(),
  age_min: z.coerce.number().optional(),
  age_max: z.coerce.number().optional(),
  gender: z.string().optional(),
  interests: z.string().optional(),
  pain_points: z.string().optional(),
  existing_customer_profile: z.string().optional(),
  product_name: z.string().optional(),
  product_pricing: z.string().optional(),
  product_features: z.string().optional(),
  product_benefits: z.string().optional(),
  product_landing_url: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

const STEPS = ['Business', 'Goal', 'Budget', 'Audience', 'Products', 'Review'];

function splitList(value?: string): string[] {
  return (value ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function toPayload(v: FormValues): OnboardingPayload {
  return {
    business_name: v.business_name,
    description: v.description,
    industry: v.industry,
    website_url: v.website_url || null,
    product_service_description: v.product_service_description || null,
    usp: v.usp || null,
    location: v.location || null,
    target_countries: splitList(v.target_countries),
    target_cities: splitList(v.target_cities),
    languages: splitList(v.languages).length ? splitList(v.languages) : ['en'],
    goal: v.goal,
    budget: {
      daily_budget: v.daily_budget,
      monthly_budget: v.monthly_budget,
      currency: v.currency.toUpperCase(),
      max_cpa: v.max_cpa ?? null,
      target_roas: v.target_roas ?? null,
    },
    audience: {
      age_min: v.age_min ?? null,
      age_max: v.age_max ?? null,
      gender: v.gender || null,
      locations: [],
      interests: splitList(v.interests),
      pain_points: splitList(v.pain_points),
      existing_customer_profile: v.existing_customer_profile || null,
    },
    products: v.product_name
      ? [
          {
            name: v.product_name,
            pricing: v.product_pricing || null,
            features: splitList(v.product_features),
            benefits: splitList(v.product_benefits),
            landing_url: v.product_landing_url || null,
          },
        ]
      : [],
  };
}

export default function OnboardingPage() {
  const router = useRouter();
  const { org } = useCurrentOrg();
  const existing = useOnboarding(org?.id);
  const save = useSaveOnboarding(org?.id ?? '');
  const [step, setStep] = useState(0);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { currency: 'USD', goal: 'generate_leads', languages: 'en' },
  });
  const { register, handleSubmit, watch, setValue, trigger, formState } = form;

  const stepFields: (keyof FormValues)[][] = [
    ['business_name', 'description', 'industry'],
    ['goal'],
    ['daily_budget', 'monthly_budget', 'currency'],
    [],
    [],
    [],
  ];

  async function next() {
    const valid = await trigger(stepFields[step]);
    if (valid) setStep((s) => Math.min(STEPS.length - 1, s + 1));
  }

  async function onSubmit(values: FormValues) {
    if (!org?.id) return;
    try {
      await save.mutateAsync(toPayload(values));
      toast.success('Business profile saved');
      router.push('/campaigns');
    } catch {
      toast.error('Could not save onboarding');
    }
  }

  const goal = watch('goal');

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Business onboarding</h1>
        <p className="text-sm text-muted-foreground">
          {existing.data ? 'Update your business information.' : 'Tell the AI about your business.'}
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-xs text-muted-foreground">
          {STEPS.map((label, i) => (
            <span key={label} className={cn(i === step && 'font-semibold text-foreground')}>
              {label}
            </span>
          ))}
        </div>
        <Progress value={((step + 1) / STEPS.length) * 100} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[step]}</CardTitle>
          <CardDescription>
            Step {step + 1} of {STEPS.length}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {step === 0 && (
                <>
                  <Field
                    label="Business name"
                    name="business_name"
                    register={register}
                    error={formState.errors.business_name?.message}
                  />
                  <div className="space-y-2">
                    <Label htmlFor="description">Business description</Label>
                    <Textarea id="description" {...register('description')} />
                    {formState.errors.description && (
                      <p className="text-xs text-destructive">
                        {formState.errors.description.message}
                      </p>
                    )}
                  </div>
                  <Field
                    label="Industry / category"
                    name="industry"
                    register={register}
                    error={formState.errors.industry?.message}
                  />
                  <Field
                    label="Website URL"
                    name="website_url"
                    register={register}
                    placeholder="https://"
                  />
                  <Field label="Unique selling proposition" name="usp" register={register} />
                  <Field label="Business location" name="location" register={register} />
                </>
              )}

              {step === 1 && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {GOALS.map((g) => (
                    <button
                      type="button"
                      key={g.value}
                      onClick={() => setValue('goal', g.value)}
                      className={cn(
                        'rounded-lg border p-4 text-left transition-colors',
                        goal === g.value ? 'border-primary bg-primary/5' : 'hover:bg-accent',
                      )}
                    >
                      <p className="font-medium">{g.label}</p>
                      <p className="text-xs text-muted-foreground">{g.hint}</p>
                    </button>
                  ))}
                </div>
              )}

              {step === 2 && (
                <>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field
                      label="Daily budget"
                      name="daily_budget"
                      type="number"
                      register={register}
                      error={formState.errors.daily_budget?.message}
                    />
                    <Field
                      label="Monthly budget"
                      name="monthly_budget"
                      type="number"
                      register={register}
                      error={formState.errors.monthly_budget?.message}
                    />
                    <Field label="Currency" name="currency" register={register} />
                    <Field
                      label="Max acceptable CPA"
                      name="max_cpa"
                      type="number"
                      register={register}
                    />
                    <Field
                      label="Target ROAS (optional)"
                      name="target_roas"
                      type="number"
                      register={register}
                    />
                  </div>
                  <Field
                    label="Target countries (comma separated)"
                    name="target_countries"
                    register={register}
                    placeholder="United States, Canada"
                  />
                  <Field
                    label="Target cities (comma separated)"
                    name="target_cities"
                    register={register}
                  />
                </>
              )}

              {step === 3 && (
                <>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Age min" name="age_min" type="number" register={register} />
                    <Field label="Age max" name="age_max" type="number" register={register} />
                    <Field label="Gender" name="gender" register={register} placeholder="all" />
                  </div>
                  <Field label="Interests (comma separated)" name="interests" register={register} />
                  <Field
                    label="Customer pain points (comma separated)"
                    name="pain_points"
                    register={register}
                  />
                  <div className="space-y-2">
                    <Label htmlFor="existing_customer_profile">Existing customer profile</Label>
                    <Textarea
                      id="existing_customer_profile"
                      {...register('existing_customer_profile')}
                    />
                  </div>
                </>
              )}

              {step === 4 && (
                <>
                  <Field label="Product / service name" name="product_name" register={register} />
                  <Field
                    label="Pricing"
                    name="product_pricing"
                    register={register}
                    placeholder="$29/mo"
                  />
                  <Field
                    label="Features (comma separated)"
                    name="product_features"
                    register={register}
                  />
                  <Field
                    label="Benefits (comma separated)"
                    name="product_benefits"
                    register={register}
                  />
                  <Field
                    label="Landing page URL"
                    name="product_landing_url"
                    register={register}
                    placeholder="https://"
                  />
                </>
              )}

              {step === 5 && (
                <div className="space-y-2 text-sm">
                  <Summary label="Business" value={watch('business_name')} />
                  <Summary label="Industry" value={watch('industry')} />
                  <Summary label="Goal" value={GOALS.find((g) => g.value === goal)?.label} />
                  <Summary
                    label="Daily budget"
                    value={`${watch('currency')} ${watch('daily_budget') || ''}`}
                  />
                  <p className="pt-2 text-muted-foreground">
                    Save your profile, then generate an AI campaign strategy from the Campaigns
                    page.
                  </p>
                </div>
              )}
            </motion.div>

            <div className="mt-6 flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                <ArrowLeft className="size-4" /> Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="button" onClick={() => void next()}>
                  Next <ArrowRight className="size-4" />
                </Button>
              ) : (
                <Button type="submit" disabled={save.isPending}>
                  {save.isPending ? <Spinner className="size-4" /> : <Check className="size-4" />}
                  Save profile
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  name,
  register,
  type = 'text',
  placeholder,
  error,
}: {
  label: string;
  name: keyof FormValues;
  register: UseFormRegister<FormValues>;
  type?: string;
  placeholder?: string;
  error?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} type={type} placeholder={placeholder} {...register(name)} />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function Summary({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex justify-between border-b py-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '—'}</span>
    </div>
  );
}
