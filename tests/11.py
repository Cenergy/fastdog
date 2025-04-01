from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests,os
import dashscope
from dashscope import ImageSynthesis

# 填写dashscope key
dashscope.api_key =  os.environ.get("DASHSCOPE_API_KEY")

def simple_call():

    # 文本提示
    prompt = '画一张大数据平台技术架构图'

    ''' 调用模型并设置入参
        model: 模型名称
        n:数量
        size:图片尺寸
    '''
    rsp = ImageSynthesis.call(model=ImageSynthesis.Models.wanx_v1,
                              prompt=prompt,
                              n=4,
                              size='1024*1024')

    # 响应ok
    if rsp.status_code == HTTPStatus.OK:
        # 遍历结果
        for result in rsp.output.results:
            file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
            # 保存图片
            with open('./%s' % file_name, 'wb+') as f:
                f.write(requests.get(result.url).content)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    simple_call()
