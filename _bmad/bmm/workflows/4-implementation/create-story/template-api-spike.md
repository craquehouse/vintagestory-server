# Story {{epic_num}}.0: {{epic_title}} - API Research Spike

Status: ready-for-dev

<!--
API SPIKE STORY TEMPLATE
========================
Use this template for epics that depend on external APIs (VintageStory Mod API,
third-party services, etc.). The spike should be Story X.0 and complete BEFORE
starting implementation stories.

Purpose:
- Discover API quirks, limitations, and undocumented behaviors
- Document field semantics (types, formats, edge cases)
- Create test fixtures from real API responses
- Prevent mid-story pivots when API doesn't work as assumed

When to use:
- Epic involves browsing/searching external data
- Epic integrates with third-party services
- Epic depends on APIs not previously used in project
- Prior epic had API-related pivots (learn from experience)
-->

## Story

As a **developer**,
I want to **research and document the {{api_name}} API behavior**,
so that **implementation stories can proceed without mid-story pivots due to API surprises**.

## Acceptance Criteria

1. API endpoint documentation created with actual response examples
2. Field semantics documented (types, formats, null handling)
3. API limitations and quirks documented
4. Test fixtures created from real API responses
5. Recommended patterns documented for implementation stories

## Tasks / Subtasks

- [ ] Task 1: API endpoint exploration + documentation
  - [ ] List all relevant endpoints for this epic
  - [ ] Document request parameters and their effects
  - [ ] Document response structure with real examples
  - [ ] Note any pagination, rate limiting, or caching headers

- [ ] Task 2: Field semantics analysis
  - [ ] Document each field's type and format (dates, enums, nullability)
  - [ ] Identify any fields with unexpected semantics
  - [ ] Note fields that differ from documentation (if any)
  - [ ] Document default values and edge cases

- [ ] Task 3: Limitations and quirks documentation
  - [ ] Document any filtering/sorting limitations
  - [ ] Note fields that can't be used as expected
  - [ ] Identify workarounds needed (client-side filtering, etc.)
  - [ ] Document error responses and failure modes

- [ ] Task 4: Test fixture creation
  - [ ] Create representative API response fixtures
  - [ ] Include edge cases (empty lists, null fields, large responses)
  - [ ] Store in appropriate test fixtures location
  - [ ] Document fixture usage in tests

- [ ] Task 5: Pattern recommendations + summary
  - [ ] Recommend architecture patterns based on findings
  - [ ] Document any decisions that need to be made by team
  - [ ] Update epic stories if scope changes needed
  - [ ] Create backlog items for discovered limitations

## Dev Notes

### Research Focus Areas

Document findings for each area:

1. **Pagination**: How does it work? Offset vs cursor? Page size limits?
2. **Filtering**: What filters are supported server-side vs need client-side?
3. **Sorting**: What sort options exist? How are ties handled?
4. **Search**: Full-text? Partial match? Which fields searchable?
5. **Caching**: Cache headers? Recommended refresh intervals?
6. **Rate Limits**: Documented limits? Observed throttling?

### Output Artifacts

This spike should produce:

1. **API Documentation** - Add to `agentdocs/{{api_slug}}.md`
2. **Test Fixtures** - Add to appropriate test directory
3. **Architecture Recommendations** - Update epic stories or architecture.md
4. **Backlog Items** - For limitations requiring workarounds

### References

- Existing API documentation: [link if available]
- Related agentdocs: `agentdocs/vintagestory-modapi.md` (example)
- `project-context.md` - Development patterns

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Findings Summary

<!-- Populate during spike execution -->

### API Quirks Discovered

<!-- List unexpected behaviors found -->

### Architecture Decisions Made

<!-- Document key decisions and rationale -->

### Backlog Items Created

<!-- Link to any polish-backlog or story items created -->
