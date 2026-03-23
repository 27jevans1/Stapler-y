from desktop_pet import DesktopPet


if __name__ == "__main__":
    try:
        pet = DesktopPet()
        pet.run()
    except Exception as e:
        print(f"Error starting desktop pet: {e}")
        import traceback
        traceback.print_exc()

# Testing
