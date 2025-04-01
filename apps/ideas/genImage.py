import os
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
import dashscope
from dashscope import ImageSynthesis
from enum import Enum

from core.constants import ProviderType

class ImageGenerator:
    """
    图片生成器类，支持多种AI图片生成服务
    
    特性:
    - 支持通义万相和HuggingFace两种生成方式
    - 灵活的尺寸配置，支持预设尺寸和自定义尺寸
    - 详细的错误处理和日志记录
    - 易于扩展新的图片生成服务
    
    使用示例:
        >>> generator = ImageGenerator()  # 默认使用通义万相
        >>> result = generator.generate(
        ...     prompt="一幅美丽的风景画",
        ...     output_dir="./output",
        ...     n=1,
        ...     size="1024*768"
        ... )
    """
    
    def __init__(self, provider=ProviderType.WANX, default_size="1024*768"):
        """
        初始化图片生成器
        
        参数:
            provider (ProviderType): 图片生成服务提供商，默认为通义万相
            default_size (str): 默认图片尺寸，格式为"宽*高"或"宽x高"
        
        异常:
            ValueError: 当缺少必要的API密钥时抛出
        """
        self.provider = provider
        self.default_size = default_size
        
        # 初始化API密钥
        self._initialize_api_keys()
        
    def _initialize_api_keys(self):
        """
        初始化API密钥
        
        根据provider类型设置对应的API密钥
        """
        if self.provider == ProviderType.WANX:
            self.api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "请设置DASHSCOPE_API_KEY环境变量以使用通义万相服务"
                )
            dashscope.api_key = self.api_key
        elif self.provider == ProviderType.HUGGINGFACE:
            self.api_key = os.environ.get("HF_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "请设置HF_API_KEY环境变量以使用HuggingFace服务"
                )
    
    def generate(self, prompt, output_dir, n=1, size=None, **kwargs):
        """
        生成图片
        
        参数:
            prompt (str): 生成图片的文本提示
            output_dir (str): 图片输出目录路径
            n (int): 生成图片数量，默认为1
            size (str|tuple): 图片尺寸，可以是:
                - 字符串格式的"宽*高"或"宽x高"
                - 元组格式的(width, height)
                - 预设尺寸名称(如'square_large')
                - 如果为None，使用默认尺寸
            **kwargs: 传递给具体生成服务的额外参数
        
        返回:
            dict: 包含生成状态和结果信息的字典
                {
                    'status': 'completed'|'failed',
                    'results': [result1, result2, ...],
                    'error_message': str (仅在失败时存在)
                }
                
        异常:
            ValueError: 当尺寸参数无效时抛出
            OSError: 当无法创建输出目录时抛出
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 处理尺寸参数
            processed_size = self._process_size_parameter(size)
            
            # 根据provider选择生成方法
            if self.provider == ProviderType.WANX:
                return self._generate_with_wanx(prompt, output_dir, n, processed_size, **kwargs)
            elif self.provider == ProviderType.HUGGINGFACE:
                return self._generate_with_huggingface(prompt, output_dir, n, processed_size, **kwargs)
            
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': f"生成图片时发生错误: {str(e)}"
            }
    
    def _process_size_parameter(self, size):
        """
        处理尺寸参数，统一转换为字符串格式的"宽*高"
        
        参数:
            size (str|tuple|None): 输入的尺寸参数
        
        返回:
            str: 统一格式的尺寸字符串"宽*高"
            
        异常:
            ValueError: 当尺寸参数无效时抛出
        """
        if size is None:
            return self.default_size
            
        supported_sizes = get_supported_sizes()
        
        # 处理预设尺寸名称
        if isinstance(size, str) and size in supported_sizes:
            return supported_sizes[size]
            
        # 处理元组格式的尺寸
        if isinstance(size, tuple) and len(size) == 2:
            return f"{size[0]}*{size[1]}"
            
        # 处理字符串格式的尺寸
        if isinstance(size, str) and ('*' in size or 'x' in size):
            size = size.replace('x', '*')
            try:
                width, height = map(int, size.split('*'))
                if width <= 0 or height <= 0:
                    raise ValueError("尺寸必须为正整数")
                return size
            except ValueError:
                raise ValueError(f"无效的尺寸格式: {size}, 应为'宽*高'或'宽x高'")
        
        raise ValueError(
            f"无效的尺寸参数: {size}, 支持的尺寸名称: {list(supported_sizes.keys())}, "
            f"或自定义'宽*高'/'宽x高'格式"
        )
        
    def _generate_with_wanx(self, prompt, output_dir, n, size, **kwargs):
        """
        使用通义万相API生成图片
        
        参数:
            prompt (str): 生成图片的文本提示
            output_dir (str): 图片输出目录路径
            n (int): 生成图片数量
            size (str): 图片尺寸，格式为"宽*高"
            **kwargs: 传递给通义万相API的额外参数
        
        返回:
            dict: 包含生成状态和结果信息的字典
        """
        
        try:
            # 调用通义万相API
            rsp = ImageSynthesis.call(
                model=ImageSynthesis.Models.wanx_v1,
                prompt=prompt,
                n=n,
                size=size,
                **kwargs
            )
            
            # 处理API响应
            if rsp.status_code == HTTPStatus.OK:
                print(f'[INFO] 通义万相API调用成功，输出对象: {rsp.output}')
                
                # 检查返回结果是否为空
                if not hasattr(rsp.output, 'results') or not rsp.output.results:
                    warning_msg = f'返回结果为空，请检查prompt参数: {prompt}'
                    print(f'[WARNING] {warning_msg}')
                    return {
                        'status': 'completed',
                        'results': [],
                        'warning': warning_msg
                    }
                
                # 处理并保存生成的图片
                results = []
                for result in rsp.output.results:
                    file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                    output_path = os.path.join(output_dir, file_name)
                    
                    # 下载并保存图片
                    self._download_and_save_image(result.url, output_path)
                    
                    results.append({
                        'status': 'completed',
                        'result_path': output_path
                    })
                
                return {
                    'status': 'completed',
                    'results': results
                }
            else:
                error_msg = (
                    f'通义万相API调用失败, status_code: {rsp.status_code}, '
                    f'code: {rsp.code}, message: {rsp.message}'
                )
                print(f'[ERROR] {error_msg}')
                return {
                    'status': 'failed',
                    'error_message': error_msg
                }
                
        except Exception as e:
            error_msg = f'通义万相图片生成过程中发生异常: {str(e)}'
            print(f'[ERROR] {error_msg}')
            return {
                'status': 'failed',
                'error_message': error_msg
            }
            
    def _download_and_save_image(self, image_url, output_path):
        """
        下载并保存图片
        
        参数:
            image_url (str): 图片URL
            output_path (str): 图片保存路径
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            with open(output_path, 'wb+') as f:
                f.write(response.content)
            
            print(f'[INFO] 图片已保存至: {output_path}')
        except Exception as e:
            print(f'[ERROR] 下载或保存图片失败: {str(e)}')
            raise
    
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
        'square_xlarge': '1536*1536',
        'landscape_small': '768*512',
        'landscape_medium': '1024*768',
        'landscape_large': '1536*1024',
        'portrait_small': '512*768',
        'portrait_medium': '768*1024',
        'portrait_large': '1024*1536',
        'hd': '1280*720',
        'full_hd': '1920*1080',
        'ultra_hd': '3840*2160'
    }