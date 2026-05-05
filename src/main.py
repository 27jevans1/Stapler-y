# Explicit imports so PyInstaller's static analyser always bundles
# these local modules regardless of working directory or environment.
import chat_win  # noqa: F401
import ai        # noqa: F401
import history   # noqa: F401
import elderCore # noqa: F401

from desktop_pet import DesktopPet


if __name__ == "__main__":
    try:
        pet = DesktopPet()
        pet.run()
    except Exception as e:
        print(f"Error starting desktop pet: {e}")
        import traceback
        traceback.print_exc()
