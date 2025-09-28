# Bus Hound Lite

Bus Hound Lite 是一个专为 **Windows** 平台设计的命令行工具，用于模拟 Bus Hound 的常用功能。它能够在用户态环境中监控 USB 设备的热插拔事件，并将串口通信记录为结构化的 JSON 日志，帮助嵌入式和驱动开发人员在 Windows 桌面环境中快速定位问题。

## 功能概述

- **USB 监控**：
  - 自动检测 USB 设备的插入和拔出事件（仅支持 Windows 10/11）。
  - 自动提取厂商 ID、产品 ID、设备地址等基础信息。
  - 通过周期性轮询 `pyusb` 检测设备列表变化，部署简单，无需手动维护消息循环。

- **串口监控**：
  - 通过 [`pyserial`](https://pyserial.readthedocs.io/) 捕获串口输入数据。
  - 将原始数据以十六进制字符串的形式输出，便于后续分析或导入到其他工具中。
  - 通过 `--baudrate` 参数快速调整串口波特率。

- **JSON 日志输出**：
  - 所有事件均使用统一的 JSON 结构输出，支持写入到文件或标准输出。
  - 方便与现有的日志收集或数据分析流水线整合。

## 安装依赖

```bash
pip install -r requirements.txt
```

该项目仅支持 Windows 平台，使用前需要在目标设备上安装 [`libusb`](https://libusb.info/) 驱动，以便 `pyusb` 能够访问硬件。

## 使用示例

监控 USB 热插拔事件并输出到终端：

```bash
python -m bus_hound_tool.cli --usb
```

同时监控 USB 和串口，并将所有事件追加写入 `logs/session.jsonl`：

```bash
python -m bus_hound_tool.cli --usb --serial COM3 --log-file logs/session.jsonl
```

## 事件格式

示例 USB 事件：

```json
{
  "action": "attach",
  "timestamp": "2024-05-18T12:30:11.123456Z",
  "device": {
    "vendor_id": "0x1234",
    "product_id": "0xabcd",
    "bus": "1",
    "address": "5",
    "manufacturer": "Demo",
    "product": "Virtual USB Device",
    "serial_number": "ABCDEF"
  }
}
```

示例串口事件：

```json
{
  "timestamp": "2024-05-18T12:31:02.000001Z",
  "direction": "in",
  "payload": "48656c6c6f20555342"
}
```

## 开发与测试

项目使用 `pytest` 编写单元测试：

```bash
pytest
```

由于测试环境通常无法访问真实硬件，测试中通过注入模拟的串口对象和伪造的 USB 枚举结果来确保逻辑正确。

## 许可证

MIT License
