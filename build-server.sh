#!/bin/bash
# Clean up files not needed for building the archive
for dir in "__pycache__" "*.egg-info" "build" "dist"; do
    find . -name "$dir" -type d -exec rm -rf {} +
done

# Replace shared symlink with actual files
rm server/avala/shared 2>/dev/null || true
mkdir -p server/avala/shared
rm server/avala/shared/* 2>/dev/null || true
cp -r shared/* server/avala/shared/

# Clone frontend
temp_dir=$(mktemp -d)
original_cwd=$(pwd)
git clone git@github.com:dusanlazic/avala-dashboard.git "$temp_dir"
cd "$temp_dir"

# Build frontend
npm install
npm run build -- --outDir "$original_cwd/server/avala/static/dist"
cd "$original_cwd"

# Clean up
rm -rf "$temp_dir"

# Build archive
cd server/
python setup.py sdist
cd ..

# Move archive to cwd
mv server/dist/* .

# Revert symlink
rm -r server/avala/shared
ln -s ../../shared/ server/avala/shared

# Clean up
for dir in "__pycache__" "*.egg-info" "build" "dist"; do
    find . -name "$dir" -type d -exec rm -rf {} +
done