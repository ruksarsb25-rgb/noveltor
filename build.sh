#!/usr/bin/env bash
set -e

echo "Installing LaTeX (texlive)..."
apt-get update
apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    cm-super \
    dvipng

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Build complete!"
