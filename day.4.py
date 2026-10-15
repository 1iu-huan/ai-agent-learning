#要以读文件的模式打开一个文件对象，使用Python内置的open()函数，传入文件名和标示符
#标示符'r'表示读，这样，我们就成功地打开了一个文件。
#标识符'w'表示写
#例：f = open('/Users/michael/test.txt', 'r')
#如果文件打开成功，接下来，调用read()方法可以一次读取文件的全部内容，Python把内容读到内存，用一个str对象表示
#最后一步是调用close()方法关闭文件。文件使用完毕后必须关闭，因为文件对象会占用操作系统的资源，并且操作系统同一时间能打开的文件数量也是有限的
#Python引入了with语句来自动帮我们调用close()方法


#读read,写write

with open('/path/to/file', 'r',encoding='utf-8') as f:
    print('文件的内容是')
    print(f.read())

with open('/Users/michael/test.txt', 'w',encoding='utf-8') as f:
    f.write('Hello, world!')


#使用try...except捕获错误还有一个巨大的好处，就是可以跨越多层调用，比如函数main()调用bar()，bar()调用foo()，结果foo()出错了，这时，只要main()捕获到了，就可以处理
def foo(s):
    return 10 / int(s)

def bar(s):
    return foo(s) * 2

def main():
    try:
        bar('0')
    except Exception as e:
        print('Error:', e)
    finally:
        print('finally...')

#Python内置的logging模块可以非常容易地记录错误信息
#raise语句抛出一个错误的实例

if __name__ == '__main__':
#高级语言通常都内置了一套try...except...finally...的错误处理机制，Python也不例外
    try:
        print('try...')
        r = 10 / 0
        print('result:', r)
    except ZeroDivisionError as e:
        print('except:', e)
    finally:
        print('finally...')
    print('END')

#可以有多个except来捕获不同类型的错误：
    try:
        print('try...')
        r = 10 / int('a')
        print('result:', r)
    except ValueError as e:
        print('ValueError:', e)
    except ZeroDivisionError as e:
        print('ZeroDivisionError:', e)
    finally:
        print('finally...')
    print('END')

#此外，如果没有错误发生，可以在except语句块后面加一个else，当没有错误发生时，会自动执行else语句
    try:
        print('try...')
        r = 10 / int('2')
        print('result:', r)
    except ValueError as e:
        print('ValueError:', e)
    except ZeroDivisionError as e:
        print('ZeroDivisionError:', e)
    else:
        print('no error!')
    finally:
        print('finally...')
    print('END')



