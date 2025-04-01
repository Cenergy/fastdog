import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps.ideas.genImage import ImageGenerator, get_supported_sizes

def test_wanx_generation():
    """测试通义万相图片生成"""
    # 确保设置了环境变量
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("请先设置DASHSCOPE_API_KEY环境变量")
        return
    
    # 文本提示
    prompt = '画一张大数据平台技术架构图'
    
    # 使用默认参数（通义万相）
    output_dir = './output/wanx'
    generator = ImageGenerator()
    result = generator.generate(
        prompt=prompt,
        output_dir=output_dir,
        n=1,
        size='square_large'  # 1024*1024
    )
    
    print(f"通义万相生成结果: {result}")

def test_hf_generation():
    """测试HuggingFace图片生成"""
    # 确保设置了环境变量
    if not os.environ.get("HF_API_KEY"):
        print("请先设置HF_API_KEY环境变量")
        return
    
    # 文本提示
    prompt = '一幅现代城市风景画'
    
    # 使用HuggingFace API
    output_dir = './output/hf'
    generator = ImageGenerator(provider=ImageGenerator.ProviderType.HUGGINGFACE)
    result = generator.generate(
        prompt=prompt,
        output_dir=output_dir,
        n=1,
        size='landscape_medium'  # 1024*768
    )
    
    print(f"HuggingFace生成结果: {result}")

def test_different_sizes():
    """测试不同尺寸的图片生成"""
    # 获取支持的尺寸
    sizes = get_supported_sizes()
    print("支持的图片尺寸:")
    for name, dimensions in sizes.items():
        print(f"  {name}: {dimensions}")

if __name__ == '__main__':
    # 测试不同尺寸
    test_different_sizes()
    
    # 根据需要取消注释以下测试
    # test_wanx_generation()
    # test_hf_generation()
    
    print("\n提示: 要使用通义万相API，请设置环境变量 DASHSCOPE_API_KEY")
    print("要使用HuggingFace API，请设置环境变量 HF_API_KEY")