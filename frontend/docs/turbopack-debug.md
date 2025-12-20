# Turbopack Debug Notes

## When dev panics
- Check the latest panic log:
  - PowerShell: `.\scripts\show-latest-panic-log.ps1`
- Common causes:
  - Recursive symlinks or nested `node_modules` loops.
  - Custom webpack config or loaders not supported by Turbopack.
  - Importing server-only modules (fs/path/etc.) in client components.

## Fallback to Webpack
- Default dev/build is Webpack for stability on Windows:
  - `npm run dev` (uses `next dev --webpack -p 5000`)
  - `npm run dev:turbo` to try Turbopack
  - `npm run build` (uses `next build --webpack`)

## Cleanup steps
- Remove `.next`, `node_modules`, and reinstall if panics persist:
  - `Remove-Item -Recurse -Force .next, node_modules` (PowerShell)
  - `npm cache verify && npm install`

## Re-enabling Turbopack
- Use `npm run dev:turbo` to test.
- Ensure no recursive symlinks and avoid unsupported webpack customizations.
