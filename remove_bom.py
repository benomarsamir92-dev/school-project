import os
import glob

def remove_bom_from_po_files():
    # Find all .po files in the locale directory
    po_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.po'):
                po_files.append(os.path.join(root, file))
    
    for po_file in po_files:
        print(f"Processing: {po_file}")
        
        # Read file in binary mode
        with open(po_file, 'rb') as f:
            content = f.read()
        
        # Check and remove BOM
        if content.startswith(b'\xef\xbb\xbf'):
            print(f"  Removing BOM from {po_file}")
            content = content[3:]  # Remove first 3 bytes (BOM)
            
            # Write back without BOM
            with open(po_file, 'wb') as f:
                f.write(content)
            print(f"  Fixed: {po_file}")
        else:
            print(f"  No BOM found in {po_file}")

# Run the function
remove_bom_from_po_files()
