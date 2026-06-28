import math

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush


class ProductionCurveTableWidget(QWidget):
    """
    生产动态曲线数据表格。

    功能：
    1. 接收和线图相同的 data
    2. 表格显示所有可用属性
    3. 表头显示中文属性名
    4. 点击表格某一行时，向外发送 row_selected(row)
    5. 支持外部调用 select_row_by_index(row)，自动选中并滚动到对应行
    6. 当线图点击某个数据点时，对应表格行显示为蓝色底、白色字
    """

    # 表格行点击信号，参数是行号 row_index
    row_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = None

        # 当前被线图或表格选中的行
        self.current_marked_row = None

        # 标记颜色
        self.mark_background_color = QColor(0, 120, 215)
        self.mark_text_color = QColor(255, 255, 255)

        # 普通文字颜色
        self.normal_text_color = QColor(0, 0, 0)

        self.property_display_names = {
            "CumOil": "累积产油量",
            "CumWater": "累积产水量",
            "CumGas": "累积产气",
            "Qo": "产油速率",
            "Qw": "产水速率",
            "Qg": "产气速率",
            "BHP": "井底流压",
            "AvgPressure": "平均压力",
        }

        self.display_name_to_key = {
            display_name: key
            for key, display_name in self.property_display_names.items()
        }

        self.property_order = [
            "CumOil",
            "CumWater",
            "CumGas",
            "Qo",
            "Qw",
            "Qg",
            "BHP",
            "AvgPressure",
        ]

        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.table = QTableWidget()
        root_layout.addWidget(self.table)

        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # 强制选中行显示为蓝色底、白色字
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: rgb(0, 120, 215);
                color: white;
            }
        """)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.verticalHeader().setVisible(False)

        self.table.cellClicked.connect(self._on_cell_clicked)

    def set_data(self, data):
        """
        设置数据。
        data 应该和 ProductionCurvePlotWidget 里的 data 一样。
        """
        self.data = data

    def show_all_properties(self):
        """
        显示所有可用属性。
        """
        if self.data is None:
            self.clear_table()
            return

        if "date" not in self.data:
            self.clear_table()
            return

        keys = self.get_available_property_keys()

        if not keys:
            self.clear_table()
            return

        self._show_properties_by_keys(keys)

    def show_selected_properties(self, property_names):
        """
        保留备用。
        如果以后想让表格只显示选中属性，可以再用它。
        """
        if self.data is None:
            self.clear_table()
            return

        if "date" not in self.data:
            self.clear_table()
            return

        keys = []

        for name in property_names:
            key = self._normalize_property_name(name)

            if key in self.data and key != "date":
                keys.append(key)

        if not keys:
            self.clear_table()
            return

        self._show_properties_by_keys(keys)

    def _show_properties_by_keys(self, keys):
        """
        按英文 key 显示表格。
        """
        dates = self.data["date"]
        row_count = len(dates)
        col_count = 1 + len(keys)

        self.table.clear()
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)

        self.current_marked_row = None

        headers = ["时间"]

        for key in keys:
            headers.append(self._get_display_name(key))

        self.table.setHorizontalHeaderLabels(headers)

        for row in range(row_count):
            time_item = QTableWidgetItem(str(dates[row]))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, time_item)

            for col, key in enumerate(keys, start=1):
                values = self.data.get(key, [])

                if row >= len(values):
                    value_text = ""
                else:
                    value_text = self._format_value(values[row])

                item = QTableWidgetItem(value_text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def get_available_property_keys(self):
        """
        获取当前表格可显示的英文字段 key。
        """
        if self.data is None:
            return []

        ordered = [
            key for key in self.property_order
            if key in self.data and key != "date"
        ]
        extra = [
            key for key in self.data.keys()
            if key not in ordered and key != "date"
        ]
        return ordered + extra

    def clear_table(self):
        """
        清空表格。
        """
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.current_marked_row = None

    def select_row_by_index(self, row_index):
        """
        外部调用：
        根据线图点击的数据点，自动选中表格对应行并滚动过去。

        效果：
        1. 对应行蓝色底
        2. 对应行白色字
        3. 自动滚动到表格中间
        """
        try:
            row_index = int(row_index)
        except Exception:
            return

        if row_index < 0 or row_index >= self.table.rowCount():
            return

        self.table.blockSignals(True)

        if self.current_marked_row is not None:
            self._reset_row_style(self.current_marked_row)

        self.current_marked_row = row_index
        self._mark_row_style(row_index)

        self.table.selectRow(row_index)

        first_item = self.table.item(row_index, 0)

        if first_item is not None:
            self.table.scrollToItem(
                first_item,
                QTableWidget.PositionAtCenter
            )

        self.table.blockSignals(False)

    def clear_selection(self):
        """
        清除表格选中状态和蓝色标记。
        """
        self.table.blockSignals(True)

        if self.current_marked_row is not None:
            self._reset_row_style(self.current_marked_row)

        self.current_marked_row = None
        self.table.clearSelection()

        self.table.blockSignals(False)

    def _mark_row_style(self, row_index):
        """
        把某一行设置为蓝色底、白色字。
        """
        if row_index < 0 or row_index >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row_index, col)

            if item is None:
                continue

            item.setBackground(QBrush(self.mark_background_color))
            item.setForeground(QBrush(self.mark_text_color))

    def _reset_row_style(self, row_index):
        """
        恢复某一行普通样式。
        """
        if row_index < 0 or row_index >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row_index, col)

            if item is None:
                continue

            item.setBackground(QBrush())
            item.setForeground(QBrush(self.normal_text_color))

    def _on_cell_clicked(self, row, column):
        """
        点击表格任意单元格时：
        1. 表格自己标记这一行
        2. 发送当前行号给线图
        """
        self.select_row_by_index(row)
        self.row_selected.emit(int(row))

    def _normalize_property_name(self, property_name):
        """
        中文属性名转英文 key。
        """
        if property_name in self.display_name_to_key:
            return self.display_name_to_key[property_name]

        return property_name

    def _get_display_name(self, key):
        """
        英文 key 转中文显示名。
        """
        return self.property_display_names.get(key, key)

    def _format_value(self, value):
        """
        格式化数值。
        """
        if value is None:
            return ""

        try:
            value = float(value)

            if not math.isfinite(value):
                return ""

            return f"{value:.6g}"

        except Exception:
            return str(value)
