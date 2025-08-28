from .models import GeoModel, GeoCategory
from fastadmin import TortoiseModelAdmin, register, action, display
from fastadmin.api.exceptions import AdminApiException
from tortoise.fields import CharField, TextField, DecimalField, BooleanField, IntField
from fastapi.responses import JSONResponse
from uuid import UUID
import json
from typing import List
from core.settings import settings



@register(GeoCategory)
class GeoCategoryAdmin(TortoiseModelAdmin):
    model = GeoCategory
    icon = "folder"
    display_name = "地理分类"
    list_display = [
        "id", "name", "description", "sort_order", 
        "is_active", "created_at", "updated_at"
    ]
    list_display_links = ["id", "name"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 20
    ordering = ["sort_order", "-created_at"]
    
    # 设置中文显示名称
    verbose_name = "地理分类"
    verbose_name_plural = "地理分类"
    
    form_fields = {
        "name": CharField(max_length=255, description="分类名称"),
        "description": TextField(description="分类描述", required=False),
        "sort_order": IntField(description="排序顺序", required=False),
        "is_active": BooleanField(description="是否可用", required=False),
    }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存模型时的数据验证和处理"""
        try:
            # 验证排序顺序
            if "sort_order" in payload and payload["sort_order"] is not None:
                sort_order = int(payload["sort_order"])
                if sort_order < 0:
                    raise AdminApiException(422, "排序顺序不能为负数")
            
            # 调用父类保存方法
            return await super().save_model(id, payload)
        
        except AdminApiException:
            # 重新抛出AdminApiException
            raise
        except Exception as e:
            # 将其他异常转换为AdminApiException
            raise AdminApiException(500, f"保存数据时发生错误: {str(e)}")
    
    @action(description="批量启用选中的分类")
    async def bulk_activate(self, ids: List[int]) -> JSONResponse:
        """批量启用分类"""
        try:
            await GeoCategory.filter(id__in=ids).update(is_active=True)
            return JSONResponse(
                content={"success": True, "message": f"已成功启用{len(ids)}个分类"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量启用失败: {str(e)}"}
            )
    
    @action(description="批量禁用选中的分类")
    async def bulk_deactivate(self, ids: List[int]) -> JSONResponse:
        """批量禁用分类"""
        try:
            await GeoCategory.filter(id__in=ids).update(is_active=False)
            return JSONResponse(
                content={"success": True, "message": f"已成功禁用{len(ids)}个分类"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量禁用失败: {str(e)}"}
            )


@register(GeoModel)
class GeoModelAdmin(TortoiseModelAdmin):
    model = GeoModel
    icon = "environment"
    display_name = "地理位置模型"
    list_display = [
        "id", "name", "model_3d_name", "latitude", "longitude", 
        "altitude", "layer_name", "is_visible", "is_active", "created_at"
    ]
    list_display_links = ["id", "name"]
    list_filter = [
        "layer_name", "is_visible", "is_active", 
        "is_interactive", "created_at"
    ]
    search_fields = ["name", "description", "layer_name"]
    list_per_page = 20
    ordering = ["-created_at"]
    
    # 设置中文显示名称
    verbose_name = "地理位置模型"
    verbose_name_plural = "地理位置模型"
    
    form_fields = {
        "name": CharField(max_length=255, description="地理模型名称"),
        "description": TextField(description="地理模型描述", required=False),
        "model_3d": CharField(max_length=255, description="关联的3D模型"),
        
        # 地理位置信息
        "longitude": DecimalField(max_digits=10, decimal_places=7, description="经度 (-180 到 180)"),
        "latitude": DecimalField(max_digits=10, decimal_places=7, description="纬度 (-90 到 90)"),
        "altitude": DecimalField(max_digits=10, decimal_places=3, description="海拔高度(米)", required=False),
        
        # 模型姿态信息
        "pitch": DecimalField(max_digits=6, decimal_places=3, description="俯仰角(度) -90到90", required=False),
        "yaw": DecimalField(max_digits=6, decimal_places=3, description="偏航角(度) 0到360", required=False),
        "roll": DecimalField(max_digits=6, decimal_places=3, description="翻滚角(度) -180到180", required=False),
        
        # 缩放信息
        "scale_x": DecimalField(max_digits=6, decimal_places=3, description="X轴缩放比例", required=False),
        "scale_y": DecimalField(max_digits=6, decimal_places=3, description="Y轴缩放比例", required=False),
        "scale_z": DecimalField(max_digits=6, decimal_places=3, description="Z轴缩放比例", required=False),
        
        # 显示控制
        "is_visible": BooleanField(description="是否在地图上显示", required=False),
        "is_interactive": BooleanField(description="是否可交互(点击、选择等)", required=False),
        
        # 层级控制
        "layer_name": CharField(max_length=100, description="图层名称", required=False),
        "z_index": IntField(description="显示层级，数值越大越靠前", required=False),
        
        # 可见性控制
        "min_zoom_level": DecimalField(max_digits=4, decimal_places=2, description="最小可见缩放级别", required=False),
        "max_zoom_level": DecimalField(max_digits=4, decimal_places=2, description="最大可见缩放级别", required=False),
        
        # 元数据
        "metadata": TextField(description="额外的元数据信息(JSON格式)", required=False),
    }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存模型时的数据验证和处理"""
        try:
            # 验证经纬度范围
            if "longitude" in payload:
                longitude = float(payload["longitude"])
                if longitude < -180 or longitude > 180:
                    raise AdminApiException(422, "经度必须在-180到180之间")
            
            if "latitude" in payload:
                latitude = float(payload["latitude"])
                if latitude < -90 or latitude > 90:
                    raise AdminApiException(422, "纬度必须在-90到90之间")
            
            # 验证角度范围
            if "pitch" in payload and payload["pitch"] is not None:
                pitch = float(payload["pitch"])
                if pitch < -90 or pitch > 90:
                    raise AdminApiException(422, "俯仰角必须在-90到90之间")
            
            if "yaw" in payload and payload["yaw"] is not None:
                yaw = float(payload["yaw"])
                if yaw < 0 or yaw > 360:
                    raise AdminApiException(422, "偏航角必须在0到360之间")
            
            if "roll" in payload and payload["roll"] is not None:
                roll = float(payload["roll"])
                if roll < -180 or roll > 180:
                    raise AdminApiException(422, "翻滚角必须在-180到180之间")
            
            # 验证缩放比例
            for scale_field in ["scale_x", "scale_y", "scale_z"]:
                if scale_field in payload and payload[scale_field] is not None:
                    scale_value = float(payload[scale_field])
                    if scale_value <= 0:
                        raise AdminApiException(422, f"{scale_field}缩放比例必须大于0")
            
            # 验证缩放级别
            if "min_zoom_level" in payload and "max_zoom_level" in payload:
                if (payload["min_zoom_level"] is not None and 
                    payload["max_zoom_level"] is not None and
                    float(payload["min_zoom_level"]) > float(payload["max_zoom_level"])):
                    raise AdminApiException(422, "最小缩放级别不能大于最大缩放级别")
            
            
            # 调用父类保存方法
            return await super().save_model(id, payload)
        
        except AdminApiException:
            # 重新抛出AdminApiException
            raise
        except Exception as e:
            # 将其他异常转换为AdminApiException
            raise AdminApiException(500, f"保存数据时发生错误: {str(e)}")
    
    @action(description="批量设置选中项为显示状态")
    async def bulk_show(self, ids: List[int]) -> JSONResponse:
        """批量显示地理模型"""
        try:
            await GeoModel.filter(id__in=ids).update(is_visible=True)
            return JSONResponse(
                content={"success": True, "message": f"已成功显示{len(ids)}个地理模型"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量显示失败: {str(e)}"}
            )
    
    @action(description="批量设置选中项为隐藏状态")
    async def bulk_hide(self, ids: List[int]) -> JSONResponse:
        """批量隐藏地理模型"""
        try:
            await GeoModel.filter(id__in=ids).update(is_visible=False)
            return JSONResponse(
                content={"success": True, "message": f"已成功隐藏{len(ids)}个地理模型"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量隐藏失败: {str(e)}"}
            )
    
    @action(description="批量设置选中项为可交互状态")
    async def bulk_enable_interaction(self, ids: List[int]) -> JSONResponse:
        """批量启用交互"""
        try:
            await GeoModel.filter(id__in=ids).update(is_interactive=True)
            return JSONResponse(
                content={"success": True, "message": f"已成功启用{len(ids)}个地理模型的交互功能"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量启用交互失败: {str(e)}"}
            )
    
    @action(description="批量设置选中项为不可交互状态")
    async def bulk_disable_interaction(self, ids: List[int]) -> JSONResponse:
        """批量禁用交互"""
        try:
            await GeoModel.filter(id__in=ids).update(is_interactive=False)
            return JSONResponse(
                content={"success": True, "message": f"已成功禁用{len(ids)}个地理模型的交互功能"}
            )
        except Exception as e:
            return JSONResponse(
                content={"success": False, "message": f"批量禁用交互失败: {str(e)}"}
            )
    
    @display
    def position_info(self, obj):
        """显示位置信息"""
        return f"({obj.latitude:.6f}, {obj.longitude:.6f}, {obj.altitude:.2f}m)"
    
    @display
    def rotation_info(self, obj):
        """显示姿态信息"""
        return f"P:{obj.pitch:.1f}° Y:{obj.yaw:.1f}° R:{obj.roll:.1f}°"
    
    @display
    def scale_info(self, obj):
        """显示缩放信息"""
        return f"({obj.scale_x:.2f}, {obj.scale_y:.2f}, {obj.scale_z:.2f})"
    
    @display
    async def model_3d_name(self, obj):
        """显示关联3D模型的名称"""
        if obj.model_3d_id:
            from apps.resources.models import Model3D
            model_3d = await Model3D.get(id=obj.model_3d_id)
            return f"{model_3d.name} ({model_3d.id})"
        return "未关联"
    
    async def get_queryset(self):
        """获取查询集，预加载关联的model_3d"""
        return self.model.all().prefetch_related('model_3d')

