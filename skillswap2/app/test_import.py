import sys
sys.path.insert(0, 'C:\\Users\\prana\\OneDrive\\Desktop\\SKILLSWAP2')

try:
    from app.schemas import User
    print("✅ SUCCESS! User class imported!")
    print(f"User class: {User}")
except AttributeError as e:
    print(f"❌ ERROR: {e}")
    
    # Try to see what IS available
    import app.schemas
    print(f"\nAvailable attributes in app.schemas:")
    print(dir(app.schemas))
    