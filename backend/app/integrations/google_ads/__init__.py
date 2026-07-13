"""Google Ads integration package.

Split into small, independently testable units:
- ``oauth``   — Ads-scoped OAuth authorization-code flow
- ``queries`` — GAQL query builders (with input validation)
- ``mappers`` — pure API-row -> schema mappers
- ``client``  — thin synchronous wrapper over the google-ads SDK
"""
