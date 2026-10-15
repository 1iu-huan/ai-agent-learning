import os

#text:要切的长文本；chunk_size:每块最多500字；overlap:相邻两块之间重叠50字，防止上下文断掉
def simple_recursive_split(text, chunk_size=500, overlap=50):
    """简化版递归切块：先按段落切，再按句子切，最后按字符切"""
    #切分优先级清单
    separators = ["\n\n", "\n", "。", "！", "？", " "]

    #核心”递归切分“函数！！！！；_split()函数”切分机器人“
    #sep_index:当前用到了第几个切分工具
    #simple_recursive_split 函数里的变量（比如 chunk_size, overlap, separators）。_split 可以直接读取。
    def _split(text, sep_index=0):
        #什么时候收工。<=chunk_size时直接返回文本，把整段包装成列表返回
        if len(text) <= chunk_size:
            return [text]
        #拿出当前的工具开始切；比如"\n\n"、"\n"等
        #text.split(sep)会把长文本按这个符号切成若干个碎片parts
        #当前的索引sep_index有没有超出列表达到编号范围（0到5），条件为直时执行
        sep = separators[sep_index] if sep_index < len(separators) else ""
        ##用工具。如果有工具，按工具切；没工具，直接拆成单字。
        #字符串（str）对象自带的 .split() 方法。
        #.split() 的作用，就是把一段长文本，切成一个列表
        parts = text.split(sep) if sep else list(text)

        #拼装碎片，控制大小
        chunks = []
        #用 current 当作一个杯子，挨个往里面倒碎片。如果倒进这个碎片，总字数没超过 500，就继续倒（current += ...）。
        current = ""
        #将parts列表里的字符串依次装入part中
        for part in parts:
            #当前+新碎片+分隔符号
            if len(current) + len(part) + len(sep) <= chunk_size:
                #一起装起来
                current += part + sep
            else:
                if current:
                    #如果超过字数了，就把current放下（chunk.apped(current),换一个新的current,把超出的放进去
                    chunks.append(current)

                current = part + sep #换一个新箱子，把这个碎片放进去
        #循环结束后，把最一个current也放好
        if current:
            chunks.append(current)

        #递归，发现某个碎片还是大于max时，重新自己调用_split()切,把切分工具换成下一个更精细的刀（sep_index + 1,比如换成换行符\n）
        #直到所有的碎片都小于max为止
        result = []#用来装最终合格的碎块
        #上一轮切出来的碎片检查
        for chunk in chunks:
            if len(chunk) > chunk_size and sep_index < len(separators) - 1:
                #递归调用自己，换下一把刀（sep_index + 1）切这块，然后拆包塞进箱子
                #这里传的是chunk！！！
                result.extend(_split(chunk, sep_index + 1))#extend扩展列表
            else:
                result.append(chunk)#碎片合格或者刀用完了，直接原样放进箱子
        return result

    #装上重叠!!!
    raw_chunks = _split(text)#原始块，接住内部函数返回的result。这里的text是外层函数的待切分的长文本
    overlapped_chunks = []
    #挨个拿出原始碎块（i是编号，chunk是碎块内容）
    for i, chunk in enumerate(raw_chunks):
        if i > 0:#如果是第一个碎块，跳过（因为第一个前面没有“上一块”）
            #从上一块尾部借来 overlap 个字，拼在当前块开头
            #raw_chunks[i - 1]：找到前一个碎块（是一个字符串）。
            #[-overlap:]：取这个字符串最后 overlap 个字符(overlap和chunk_size一起在最外层函数的参数上）
            # + chunk：把借来的“尾款”拼接到当前碎块的开头。
            chunk = raw_chunks[i - 1][-overlap:] + chunk
        #把拼好的新碎块放进新箱子
        overlapped_chunks.append(chunk)

    return overlapped_chunks


# 测试
"""for filename in os.listdir("data"):
    if filename.endswith(".txt"):
        with open(f"data/{filename}", "r", encoding="utf-8") as f:
            text = f.read()

        chunks = simple_recursive_split(text, chunk_size=500, overlap=50)
        print(f"\n=== {filename}：切出 {len(chunks)} 块 ===")
        for i, chunk in enumerate(chunks[:2]):
            print(f"--- 块 {i + 1}（{len(chunk)}字）---")
            print(chunk[:150])"""