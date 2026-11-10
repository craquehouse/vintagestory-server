# Changelog

All notable changes to this project are listed here. Versions follow [Semantic Versioning](https://semver.org).
<!-- git-cliff: end of header -->
## Unreleased

### Features

- Implement mod update evaluation rules ([2fcb443](https://github.com/craquehouse/vintagestory-server/commit/2fcb44395bbc67baa9a7ee05e183df1cce2d9291))
- Fix line length in update rule tests ([eebeb97](https://github.com/craquehouse/vintagestory-server/commit/eebeb97b4a08dc0ac11a092977667c4312256abb))
- Add mod update store and read-time status ([28b3d05](https://github.com/craquehouse/vintagestory-server/commit/28b3d055e5e8af0ac489f58c54cfc89cc2f729dc))
- Add mod update check service ([afc769c](https://github.com/craquehouse/vintagestory-server/commit/afc769c65e22cd7b2f094224e813da79eebf0fd4))
- Add mod update status and check endpoints ([aba71e8](https://github.com/craquehouse/vintagestory-server/commit/aba71e8241c523726dd621d1e3d45c4b65ce4114))
- Resolve code review findings for update checks ([f9e1302](https://github.com/craquehouse/vintagestory-server/commit/f9e1302e8c50ee4db371dab2cf1ac7526c4e4a1c))
- Contain get_mod payload errors and save serialization errors ([14b119e](https://github.com/craquehouse/vintagestory-server/commit/14b119e386748d33333e53420d5a684cd89eb048))
- Replace lone surrogates in mod database text ([f109abf](https://github.com/craquehouse/vintagestory-server/commit/f109abfd9e1acee3ac565721d7fafaf02ca95792))
- Sanitize release filenames in a shared download step ([f4394e8](https://github.com/craquehouse/vintagestory-server/commit/f4394e84729fe2830ee9a449159a35c6034cb170))
- Add strict modinfo validation for archives ([4ebac23](https://github.com/craquehouse/vintagestory-server/commit/4ebac23af589803fd284eb8139bd4f11d4834803))
- Resolve, confirm and fetch version change releases ([0acb2a7](https://github.com/craquehouse/vintagestory-server/commit/0acb2a7a73447de4e0d8ff0640c8c9963679d8e4))
- Swap mod versions with rollback ([afc88e7](https://github.com/craquehouse/vintagestory-server/commit/afc88e780fd3723a9f2c8fc396c95fd369a6f34d))
- Add mod version change endpoint ([cd1305b](https://github.com/craquehouse/vintagestory-server/commit/cd1305bf6bdeb4f336565a8431efa4aba8c126e0))
- Expose release modid in mod lookups ([a77be34](https://github.com/craquehouse/vintagestory-server/commit/a77be3485a752c2bfc582dbe0fc9823c96eab756))
- Add web API and hooks for mod updates and version changes ([5821e66](https://github.com/craquehouse/vintagestory-server/commit/5821e662f8d8225575e2651eebbfebb00f563df6))
- Show update status and check for updates in the Installed tab ([669f27b](https://github.com/craquehouse/vintagestory-server/commit/669f27b9c90ab642957aba70d8aa087ccd55e241))
- Update mods from the table with a confirmation flow ([6620a62](https://github.com/craquehouse/vintagestory-server/commit/6620a62a428171f433111e605b8ac03dc447764f))
- Switch versions of installed mods from the detail page ([ad78389](https://github.com/craquehouse/vintagestory-server/commit/ad783898ce2600164fc1b57fdbfa944abc49066f))
- Apply all compatible updates in the update service ([ea94b7d](https://github.com/craquehouse/vintagestory-server/commit/ea94b7d79dc24dda1bd042d31a575e2ba7e92dd0))
- Add POST /mods/updates/apply-all ([71755cb](https://github.com/craquehouse/vintagestory-server/commit/71755cb85c2c326160ee216183d90600e6f9a740))
- Add web API and hook for update all ([217623b](https://github.com/craquehouse/vintagestory-server/commit/217623baebad1442e0e816fcef291118720ecce1))
- Add Update all with confirmation and per-mod summary ([4c3a6ba](https://github.com/craquehouse/vintagestory-server/commit/4c3a6ba863150a0082b882f0d607507ee1c4c1d6))
- Record update status from the mod refresh job ([46ed1ff](https://github.com/craquehouse/vintagestory-server/commit/46ed1ff2f8f727ee46e0012a14eb3a3f82adf558))
- Show the mod update count in the navigation ([e1451a8](https://github.com/craquehouse/vintagestory-server/commit/e1451a8dc762766a1ded7bf41e6cce8adecfa856))
- Show available mod updates on the Dashboard ([3991c35](https://github.com/craquehouse/vintagestory-server/commit/3991c357faa80f8f0c40a446051f1c2da092d8db))
- Add the mod update webhook setting with redacted reads ([c98a061](https://github.com/craquehouse/vintagestory-server/commit/c98a0610b3d998c728bef9d18c0a4a85394c8267))
- Build and send mod update webhook alerts ([f25617a](https://github.com/craquehouse/vintagestory-server/commit/f25617ae9bc8e8e5e7d15216bb6dc2c889095bee))
- Alert the webhook once per mod and version after each check ([3f34447](https://github.com/craquehouse/vintagestory-server/commit/3f34447fb2e0e05ca5812f21c15b3834c01e62bb))
- Set or clear the mod update webhook in API settings ([7367cab](https://github.com/craquehouse/vintagestory-server/commit/7367cab555bd5a099bbf9f5a024141f5791a0505))

### Fixes

- Tolerate cache discard failures and stop temp-name collisions ([0dbda92](https://github.com/craquehouse/vintagestory-server/commit/0dbda92ce0f4ba45f03a4df978bf821ad18b0c75))
- Stop the global error toast duplicating update errors ([8ce93a7](https://github.com/craquehouse/vintagestory-server/commit/8ce93a7b3faa6f17cea7245f15889c12d8476231))
- Report each concurrent version change and track pending per mod ([34dc37a](https://github.com/craquehouse/vintagestory-server/commit/34dc37a37e32d3cfe2f1e53a43c946ab7ac735df))
- Dedupe re-uploaded versions, expose status reasons to screen readers, narrow invalidation ([412fb15](https://github.com/craquehouse/vintagestory-server/commit/412fb15d23e4d416a573c119a4ead83e0b74a2d3))
- Raise ExternalApiError from get_mod for unusable responses (VSS-d15) ([5d338fe](https://github.com/craquehouse/vintagestory-server/commit/5d338fe5fc9770e243be9aee5fd6111903e4587b))
- Isolate data errors per mod, announce results, pin no-confirm behavior ([f7fa59c](https://github.com/craquehouse/vintagestory-server/commit/f7fa59cdcdb14ebc8822a27ba5ceec28978663e0))
- Mark the closed nav group with a dot so its chevron fits ([24aea40](https://github.com/craquehouse/vintagestory-server/commit/24aea40470d610b3983e124f0cd9db573ce51f75))
- Name badge destinations for screen readers and explain the group dot ([a5e64ad](https://github.com/craquehouse/vintagestory-server/commit/a5e64ad0861a274e9a2bf8edcd5a5a095d0d031d))
- Keep the webhook out of settings load errors; name a mod in every alert ([42189f7](https://github.com/craquehouse/vintagestory-server/commit/42189f79fd4310536afe39dd5edb793fa5e54a72))
- Refuse secret keys in the generic settings path and describe webhook status ([2583e04](https://github.com/craquehouse/vintagestory-server/commit/2583e041fb8ed7e9488d5f9cd9f98c6fd19f3cca))
- Fall back to defaults for a settings file of the wrong shape ([c20ace9](https://github.com/craquehouse/vintagestory-server/commit/c20ace91e428095590647b11c3a09a6e5cba58e6))
- Check mod compatibility against the installed server, not VS_GAME_VERSION (VSS-tpe) ([abdb174](https://github.com/craquehouse/vintagestory-server/commit/abdb1743206c2c54bdf6fa601ccb39ead248c3a6))
- Accept modinfo side "Universal" instead of discarding the modinfo ([fbda13e](https://github.com/craquehouse/vintagestory-server/commit/fbda13e19ab59e62497142508c031f116cb84233))
- Re-read mods stored with filename fallback metadata at startup ([58f32a8](https://github.com/craquehouse/vintagestory-server/commit/58f32a8875edf9d058e94721fb088dc2da8ba889))
