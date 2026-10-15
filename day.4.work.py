import openai
def read_config(filename):
    try:
        with open(filename,'r',encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '配置文件不存在，请先创建文件'



if __name__ == '__main__':
    with open('txt.txt','w',encoding='utf-8') as f:
        f.write('Hello world')
        f.write('我正在学习第四天和第五天合并的内容')
    with open('txt.txt','r',encoding='utf-8') as f:
        print(f'文件的内容是 ：{f.read()}')
    try:
        with open('test.txt','r',encoding='utf-8') as f:
            print(f.read())
    except Exception as e:
        print('错误是：',e)

    print('openai 库导入成功')
    print(f'版本号:{openai.__version__}')

    print(read_config('txt.txt'))
    print(read_config('test.txt'))