import os

def check_brackets(file_path):
    print("Checking: " + file_path)
    if not os.path.exists(file_path):
        print("File not found")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check Jinja2 tags
    stack = []
    i = 0
    while i < len(content):
        if content[i:i+2] == '{{':
            stack.append(('{{', i))
            i += 2
        elif content[i:i+2] == '}}':
            if not stack or stack[-1][0] != '{{':
                print("Unexpected }} at " + str(i))
            else:
                stack.pop()
            i += 2
        elif content[i:i+2] == '{%':
            stack.append(('{%', i))
            i += 2
        elif content[i:i+2] == '%}':
            if not stack or stack[-1][0] != '{%':
                print("Unexpected %} at " + str(i))
            else:
                stack.pop()
            i += 2
        else:
            i += 1
    
    if stack:
        for tag, pos in stack:
            print("Unclosed " + tag + " at " + str(pos))
    else:
        print("All Jinja2 tags are closed correctly.")

check_brackets('templates/admin/car_form.html')
check_brackets('templates/admin/base.html')
check_brackets('templates/admin/cars.html')
