#!/bin/bash
# BitingLip CLI Setup Script for Unix/Linux/macOS

set -e

echo "🚀 Setting up BitingLip CLI..."

# Check Python version
python_version=$(python3 -V 2>&1 | grep -Po '(?<=Python )(.+)')
if [[ -z "$python_version" ]]; then
    echo "❌ Python 3 is required but not found. Please install Python 3.8 or later."
    exit 1
fi

echo "✅ Found Python $python_version"

# Install dependencies
echo "📦 Installing CLI dependencies..."
pip3 install -r requirements.txt

# Verify installation
echo "🧪 Testing CLI installation..."
if python3 bitinglip.py --help > /dev/null 2>&1; then
    echo "✅ CLI installation successful!"
else
    echo "❌ CLI installation failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "🎉 BitingLip CLI is ready!"
echo ""
echo "Quick Start:"
echo "  # Check system status (requires running services)"
echo "  python3 bitinglip.py system status"
echo ""
echo "  # List available commands"
echo "  python3 bitinglip.py --help"
echo ""
echo "  # Set API endpoint (if different from default)"
echo "  export BITINGLIP_API_URL=http://your-gateway:8080"
echo ""
echo "Environment Variables:"
echo "  BITINGLIP_API_URL      - Gateway API URL (default: http://localhost:8080)"
echo "  BITINGLIP_API_KEY      - API authentication key"
echo "  BITINGLIP_FORMAT       - Output format (table|json|csv|yaml)"
echo "  BITINGLIP_VERBOSE      - Enable verbose logging (true|false)"
echo ""
echo "For more information, see the documentation or run:"
echo "  python3 bitinglip.py --help"
