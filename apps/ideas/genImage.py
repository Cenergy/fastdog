import os
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
import dashscope
from dashscope import ImageSynthesis
from enum import Enum

class ProviderType(Enum):
    WANX = "wanx"
    HUGGINGFACE = "huggingface"

class ImageGenerator:
    """
    图片生成器类，支持通义万相和HuggingFace两种生成方式
    默认使用通义万相，默认尺寸1024*768
    """
    
    def __init__(self, provider=ProviderType.WANX, default_size="1024*768"):
        """
        初始化图片生成器
        :param provider: 生成器类型，默认为通义万相
        :param default_size: 默认图片尺寸，格式为"宽*高"
        """
        self.provider = provider
        self.default_size = default_size
        
        # 设置API密钥
        if provider == ProviderType.WANX:
            self.api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not self.api_key:
                raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
            dashscope.api_key = self.api_key
        elif provider == ProviderType.HUGGINGFACE:
            self.api_key = os.environ.get("HF_API_KEY")
            if not self.api_key:
                raise ValueError("请设置HF_API_KEY环境变量")
    
    def generate(self, prompt, output_dir, n=1, size=None, **kwargs):
        """
        生成图片
        :param prompt: 文本提示
        :param output_dir: 输出目录
        :param n: 生成数量
        :param size: 图片尺寸，默认为初始化时设置的default_size
        :param kwargs: 其他生成参数
        :return: 生成结果信息
        """
        size = size or self.default_size
        
        if self.provider == ProviderType.WANX:
            return self._generate_with_wanx(prompt, output_dir, n, size, **kwargs)
        elif self.provider == ProviderType.HUGGINGFACE:
            return self._generate_with_huggingface(prompt, output_dir, n, size, **kwargs)
    
    def _generate_with_wanx(self, prompt, output_dir, n, size, **kwargs):
        """
        使用通义万相生成图片
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 调用模型
        rsp = ImageSynthesis.call(
            model=ImageSynthesis.Models.wanx_v1,
            prompt=prompt,
            n=n,
            size=size,
            **kwargs
        )
        
        # 处理结果
        if rsp.status_code == HTTPStatus.OK:
            results = []
            for result in rsp.output.results:
                file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                output_path = os.path.join(output_dir, file_name)
                
                # 保存图片
                with open(output_path, 'wb+') as f:
                    f.write(requests.get(result.url).content)
                
                results.append({
                    'status': 'completed',
                    'result_path': output_path
                })
            
            return {
                'status': 'completed',
                'results': results
            }
        else:
            return {
                'status': 'failed',
                'error_message': f'Failed, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}'
            }
    
    def _generate_with_huggingface(self, prompt, output_dir, n, size, **kwargs):
        """
        使用HuggingFace生成图片
        这里需要根据实际HuggingFace API实现
        """
        # 实现HuggingFace生成逻辑
        # 这里只是一个示例，需要根据实际API实现
        return {
            'status': 'failed',
            'error_message': 'HuggingFace生成功能待实现'
        }


def get_supported_sizes():
    """
    获取支持的图片尺寸
    :return: 支持的尺寸字典
    """
    return {
        'square_small': '512*512',
        'square_medium': '768*768',
        'square_large': '1024*1024',
        'landscape_small': '768*512',
        'landscape_medium': '1024*768',
        'portrait_small': '512*768',
        'portrait_medium': '768*1024'
    }