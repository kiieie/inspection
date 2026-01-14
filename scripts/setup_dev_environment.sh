#!/bin/bash
# 🚀 Setup Development Environment for Industrial Inspection System

set -e

echo "🔧 Setting up Industrial Inspection System Development Environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install development dependencies
echo "📚 Installing development dependencies..."
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p cache temp_crops_console temp_crops_parallel temp_vlm_crops test_results

# Set up environment variables
echo "🌍 Setting up environment variables..."
cat > .env << 'ENVEOF'
INSPECTION_ENV=development
INSPECTION_DEBUG=1
PYTHONPATH=$(pwd)
INSPECTION_DATA_DIR=/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)
INSPECTION_EXCEL_FILE=/home/kiie/synology/Projects/R25IA04/Inspection_point_Labeling.xlsx
ENVEOF

echo "✅ Development environment setup complete!"
echo ""
echo "🚀 To start development:"
echo "   1. Activate environment: source venv/bin/activate"
echo "   2. Start hot reload: python dev_server.py"
echo "   3. Run tests: pytest test/ -v"
echo "   4. Monitor performance: python performance_monitor.py"
