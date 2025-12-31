# Story 6.0: Epic 6 Technical Preparation

**Status:** done

## Summary
Research VintageStory console commands and create configuration infrastructure for Epic 6 (Game Configuration Management).

## Key Deliverables
- Documented `/serverconfig` commands (22+ live settings, 10+ restart-required)
- Created `serverconfig-template.json` with sensible defaults
- Defined ENV_VAR_MAP (40+ VS_CFG_* → config mappings) with type coercion
- Added @tanstack/react-table dependency for data lists

## Critical Findings
- Console commands automatically persist to serverconfig.json
- Two update methods: console (live) vs file (restart required)
- Boolean syntax varies: true/false vs 0/1 depending on command

## Files Created/Modified
- `agentdocs/vs-serverconfig-commands.md` - Command reference
- `api/src/vintagestory_api/templates/serverconfig-template.json`
- `api/src/vintagestory_api/services/config_init.py` - ENV_VAR_MAP, parse_env_value()
- `api/tests/test_serverconfig_template.py` (47 tests)
- `api/tests/test_config_init.py` (58 tests)
- `web/src/lib/tanstack-table.test.ts` (12 tests)

## Key Functions
- `ENV_VAR_MAP` - Maps VS_CFG_* env vars to serverconfig.json keys with types
- `parse_env_value(value, type)` - Type coercion for string/int/bool/float
- `get_config_key_path(key)` - Handles nested keys like "WorldConfig.AllowCreativeMode"
