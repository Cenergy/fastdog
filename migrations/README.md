# 数据库迁移说明

本项目使用 Aerich 进行数据库迁移管理。

## 初始化数据库

```bash
# 初始化迁移配置
aerich init-db
```

## 创建新的迁移

当你修改了模型后，需要创建新的迁移：

```bash
# 生成迁移文件
aerich migrate
```

## 应用迁移

```bash
# 更新数据库结构
aerich upgrade
```

## 迁移历史

```bash
# 查看迁移历史
aerich history
```

## 回滚迁移

```bash
# 回滚到上一个版本
aerich downgrade
```

## 注意事项

1. 每次修改模型后都需要创建新的迁移
2. 在应用迁移前先备份数据库
3. 生产环境谨慎使用回滚操作