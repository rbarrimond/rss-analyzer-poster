import sys
print("Python Version:", sys.version)
print("Python Path:", sys.path)

try:
    import msgraph_core
    print("✅ msgraph_core imported successfully!")
except ImportError as e:
    print(f"❌ Error importing msgraph_core: {e}")
