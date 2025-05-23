#!/bin/bash

# uvのインストール（まだの場合）
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# 仮想環境の作成
echo "Creating virtual environment..."
uv venv

# 仮想環境のアクティベート
echo "Activating virtual environment..."
source .venv/bin/activate

# 依存関係のインストール
echo "Installing dependencies..."
uv pip install -e .

echo "Setup completed! You can now run the application with:"
echo "uvicorn app.main:app --reload" 