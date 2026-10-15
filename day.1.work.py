def print_hello(name):
    print(f'你好，{name}!')

def information():
    a = input('please enter your name: ')
    b = input('please enter your age: ')
    c = input('please enter your city: ')
    print(f'这是我的基础信息:\n{a}\n{b}\n{c}')
    print_hello(a)
if __name__ == '__main__':
     information()








