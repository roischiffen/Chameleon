import json
import sys

def write_cat2(data):
    with open('data/distortion_validation/category_2/distortions_20260105_002035.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('File written successfully')

if __name__ == '__main__':
    # Load JSON from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    write_cat2(data)
