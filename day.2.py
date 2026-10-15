#list,tuple,dict,set
#条件判断
def learn1():#条件判断
    #给if添加一个else语句，意思是，如果if判断是False，不要执行if的内容，去把else执行了;当然上面的判断是很粗略的，完全可以用elif做更细致的判断;elif是else if的缩写，完全可以有多个elif
    age = 19
    if age >= 18:
        print(f'you age is {age}')
        print('adult')
    elif age < 12:
        print('you age is' , age)
        print('child')
    else:
        print('you age is' , age)
        print('teenager')

    #注意：input()返回的数据是类型是str,str不能直接和整数比较，必须先把str转换成整数。Python提供了int()函数来完成这件事情
    f = input('birth:')
    birth = int(f)
    if birth < 2000 :
        print('00前')
    else:
        print('00后')

#模式匹配（match语句）
def learn2():
    #使用match语句时，我们依次用case xxx匹配，并且可以在最后（且仅能在最后）加一个case _表示“任意值”，代码较if ... elif ... else ...更易读。
    score = 'B'
    match score:
        case 'A':
            print('score is A.')
        case 'B':
            print('score is B.')
        case 'C':
            print('score is C.')
        case _:  # _表示匹配到其他任何情况
            print('score is ???.')

    #match语句除了可以匹配简单的单个值外，还可以匹配多个值、匹配一定范围，并且把匹配后的值绑定到变量
    age = 12
    match age:
        case x if x < 10:
            print('age is' , age)
            print(f'age is {x}')#注意这两个输出，不同的表示方法，如果这个x在句子里面的话，要用格式化（以f开头）
        case 10:
            print('10 years old.')
        case 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18:
            print('11~18 years old.')
        case 19:
            print('19 years old.')
        case _:
            print('invalid age.')
#在上面这个示例中，第一个case x if x < 10表示当age < 10成立时匹配，且赋值给变量x，第二个case 10仅匹配单个值，第三个case 11|12|...|18能匹配多个值，用|分隔。


#循坏
def learn3():
    #for...in循环
    names = ['Michael', 'Bob', 'Tracy']
    for name in names:
        print(name)#所以for x in ...循环就是把每个元素代入变量x，然后执行缩进块的语句

    ai_tools = ['ChatGPT','Claude','Deepseek']
    for tool in ai_tools:
        print(tool)#带编号
    for i,tool in enumerate(ai_tools):
        print(f'{i+1}.{tool}')#不带编号

    #while循环:只要条件满足，就不断循环，条件不满足时退出循环
    sum = 0
    n = 0
    while n < 100:
        sum = sum + n
        n = n + 1
    print(sum)
    #break：在循环中，break语句可以提前退出循环
    #continue：在循环过程中，也可以通过continue语句，跳过当前的这次循环，直接开始下一次循环


if __name__ == '__main__':
    learn1()
    learn2()
    learn3()

    #list是一种有序的集合，可以随时添加和删除元素.里面的 元素的数据类型也可以不同;[]
    classmates = ['lh','yw','wh']
    print(classmates)
    print(len(classmates))
    print(classmates[0],classmates[1])#用索引来访问list中每一个元素的位置，索引从0开始
    print(classmates[-1])#-1也可以直接获取最后一个元素,同理-2，-3.当然不能越界

    #list是一个可变的有序表，所以可以往list中追加元素到末尾
    classmates.append('ys')
    print(classmates)
    #也可以插入
    classmates.insert(1,'yq')
    print(classmates)
    #删除
    classmates.pop(1)
    print(classmates)
    #替换
    classmates[0] = 'yq'
    print(classmates)

    #list可以套list
    s = ['python', 'java', 'ruby',['asp','php']]
    print(s)
    print(len(s))
    print(s[3])
    print(s[3][1])

    #tuple是元组，也是有序列表，但是tuple一但初始化就不能修改:()
    room = ('r1','r2','r3','r4','r5')
    print(room)
    #可变的tuple
    t = (1,2,3,[4,5])
    print(t[1])
    print(t[3])
    t[3][1] = 6
    print(t[3])

    #Python内置了字典：dict的支持，dict全称dictionary，在其他语言中也称为map，使用键-值（key-value）存储，具有极快的查找速度;{}
    d = {'lh': 95,'yw':80,'wh':7}
    #for循环打印字典里的每一项
    for key,value in d.items():
        print(f'{key} = {value}')

    print(d['lh'])
    d['yw'] = 90
    print(d['yw'])
    #一个key只能对应一个value。不存在key的话，将会报错。可以通过in来判断key是否存在
    print('ys' in d)
    #二是通过dict提供的get()方法，如果key不存在，可以返回None，或者自己指定的value
    print(d.get('ys',-1))
    #要删除一个key，用pop(key)方法，对应的value也会从dict中删除
    d.pop('wh')
    print(d)

    #set和dict类似，也是一组key的集合，但不存储value。由于key不能重复，所以，在set中，没有重复的key;{}
    z1 = {1,2,3}
    print(z1)
    #重复元素在set中自动被过滤
    z2 = {2,4,4,4,5,5,5}
    print(z2)
    #set可以看成数学意义上的无序和无重复元素的集合，因此，两个set可以做数学意义上的交集、并集等操作
    print(z1 & z2)
    print(z1 ^ z2)
    print(z1 | z2)






