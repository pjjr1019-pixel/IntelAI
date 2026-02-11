@echo off
cd "C:\Users\Pgiov\OneDrive\Documents\Custom programs\Intel-AI"
git checkout fix/trending-live-fallback-docs || git checkout -b fix/trending-live-fallback-docs
git add -A
git commit -m "Add live-trends toggle docs and prepare for CI"
git push -u origin fix/trending-live-fallback-docs
echo Done. Check output above for any errors.