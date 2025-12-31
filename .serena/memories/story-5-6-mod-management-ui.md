# Story 5.6: Mod Management UI

Status: done

## Summary
Full React UI for mod management including lookup, install, enable/disable, and remove.

## Components Created

### ModLookupInput
- Input with placeholder "Enter mod slug or paste URL"
- Smart URL parsing (extracts slug from full URLs)
- 300ms debounced lookup
- Preview card showing: name, author, description, side, compatibility badge
- Install button with loading state
- Confirmation dialog for incompatible mods

### CompatibilityBadge
- Compatible: Green (#a6e3a1) + checkmark
- Not verified: Yellow (#f9e2af) + warning
- Incompatible: Red (#f38ba8) + X

### ModTable
- Columns: Name, Version, Compatibility, Status (toggle), Actions (remove)
- Optimistic updates for enable/disable
- Remove confirmation dialog
- Empty state: "No mods installed yet"

### PendingRestartBanner
- Shows in header when pending_restart is true
- "⟳ Restart required · [Restart Now]"
- Restart Now triggers server restart

## TanStack Query Hooks (use-mods.ts)
- useMods() - List installed mods
- useLookupMod(slug) - Lookup mod details
- useInstallMod() - Install mutation
- useEnableMod() / useDisableMod() - Toggle mutations
- useRemoveMod() - Remove mutation

## API Functions (mods.ts)
- fetchMods(), lookupMod(), installMod()
- enableMod(), disableMod(), removeMod()

## shadcn/ui Components Added
- alert-dialog, badge, dialog, skeleton, table

## Bug Fix
VintageStory API returns lowercase `side` field ("both") - normalized in mods.py.
