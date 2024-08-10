#!/bin/bash
# Clean up files not needed for building the archive
for dir in "__pycache__" "*.egg-info" "build" "dist"; do
    find . -name "$dir" -type d -exec rm -rf {} +
done

# Replace shared symlink with actual files
rm client/avala/shared 2>/dev/null || true
mkdir -p client/avala/shared
rm client/avala/shared/* 2>/dev/null || true
cp -r shared/* client/avala/shared/

# Build archive
cd client/
python setup.py sdist
cd ..

# Move archive to cwd
mv client/dist/* .

# Revert symlink
rm -r client/avala/shared
ln -s ../../shared/ client/avala/shared

# Clean up
for dir in "__pycache__" "*.egg-info" "build" "dist"; do
    find . -name "$dir" -type d -exec rm -rf {} +
done