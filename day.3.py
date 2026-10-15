import math

def quadratic(a, b, c):
    # 1. 先计算判别式（根号里面的那部分）
    delta = b ** 2 - 4 * a * c

    # 2. 套用求根公式
    x1 = (-b + math.sqrt(delta)) / (2 * a)
    x2 = (-b - math.sqrt(delta)) / (2 * a)

    # 3. 返回两个解（Python 会自动把它们打包成一个元组）
    return x1, x2


def learm1(x):
    #对参数类型做检查，只允许整数和浮点数类型的参数。数据类型检查可以用内置函数isinstance()
    if not isinstance(x, (int, float)):
        raise TypeError('bad operand type')

    if x >= 1:
        return x
    else:
        return -x
def nop():
    pass#空函数

#函数可以返回多个值
def learn2(x,y,step,angle=0):
    nx = x + step * math.cos(angle)
    ny = y + step * math.sin(angle)
    return nx, ny
    #Python的函数返回多值其实就是返回一个tuple（元组）

#在参数前面加一个星号 *，意思是“把传进来的所有参数打包成一个元组（tuple）;可变参数
def calc(*numbers):
    total = 0
    for n in numbers:
        total = total + n * n
    return total

#在Python中定义函数，可以用必选参数、默认参数、可变参数、关键字参数和命名关键字参数，这5种参数都可以组合使用。但是请注意，参数定义的顺序必须是：必选参数、默认参数、可变参数、命名关键字参数和关键字参数。
def f1(a, b, c=0, *args, **kw):
    print('a =', a, 'b =', b, 'c =', c, 'args =', args, 'kw =', kw)

def f2(a, b, c=0, *, d, **kw):
    print('a =', a, 'b =', b, 'c =', c, 'd =', d, 'kw =', kw)



if __name__ == '__main__':
    print(learm1(-99))
    print(learn2(1,2,3))

    print('quadratic(2, 3, 1) =', quadratic(2, 3, 1))
    print('quadratic(1, 3, -4) =', quadratic(1, 3, -4))
    if quadratic(2, 3, 1) != (-0.5, -1.0):
        print('测试失败')
    elif quadratic(1, 3, -4) != (1.0, -4.0):
        print('测试失败')
    else:
        print('测试成功')

    print(calc(1, 2, 3))  # 输出 14
    print(calc(5))  # 输出 25
