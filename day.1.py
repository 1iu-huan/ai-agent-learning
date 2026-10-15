#Python程序是大小写敏感的.
def print_hello(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'hello, {name}')  # 按 Ctrl+F8 切换断点。

def number():
    a = 100
    if a >= 100:
        print(a)
    else:
        print(-a)

# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    user_input = input('please enter your name: ')
    #user_input = input();
    print(user_input)
    print_hello(user_input)

    #注意这两个的区别，number()没有返回值，在输出完number()后，程序没有结束,还有print（）在运行，由于没有返回值print()的输出结果为None
    print(number()) #输出100和None
    number() #输出100

    print_hello('world')
    print('the','刘欢')#每个字符串之间加逗号，相当于空格。
    print("hello")#字符串是以单引号和双引号括起来得到任意文本
    print('I\'m\"OK\"!')#可以用转义字符\来标识单引号和双引号

    #转义字符\;\n表示换行,\t表示制表符,\表示转义,\\表示的字符就是\
    print('I\'m ok.')
    print('I\'m learning\nPython.')

    #Python允许用'''...'''的格式表示多行内容;注意要顶格写
    print('''111
222
333''')
    print(r'''hello,\n
    world''')

    print('\\\n\\')

    #r' '表示' '内部的字符串默认不转义
    print(r'\\\n\\')

    print(100 + 200)
    print('100 + 200 =',100 + 200)#' '单引号相当于字符串
    print(10_000_000_000_000)

    print(1.23e9)
    print(1.2e-9)
    print(0.0000000012)

    #and表示与运算，or是或运算，not是非运算；
    #and是两边都为真，才是真；or是一边为真，就为真；not是把真变假，假变真
    #空值用None表示，None不能理解为0

    #变量定义
    c = 'cc'
    print(c)

    #常量：不能变的变量；通常用全部大写的变量名表示常量（习惯用法）

    #计算字符的长度
    print(len('hello'))

    #把str变为bytes，用encode()方法；把bytes变为str，用decode()方法
    #格式化
    #一种格式化字符串的方法是使用以f开头的字符串，称之为f - string，它和普通字符串不同之处在于，字符串如果包含{xxx}，就会以对应的变量替换
    s1 = 72
    s2 = 85
    r = (s2 - s1) / s1 * 100
    print(f'{r:.1f}%')

    d = 2.5
    s = 3.14 * d ** 2
    print('the area is:',s)
    print(f'the area is:{s:.2f}')
