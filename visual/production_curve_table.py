import math

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont


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
    7. 再次点击同一行时，取消高亮并发送 row_selected(-1)
    8. 表格自身点击时不自动滚动，避免界面跳动
    """

    # 表格行点击信号，参数是行号 row_index
    # row_index = -1 表示取消选中
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
            for key, display_name
            in self.property_display_names.items()
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

        # 保留隔行底色
        self.table.setAlternatingRowColors(True)

        # 禁止编辑
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        # 不使用 Qt 默认选中效果。
        # 蓝色底、白色字完全由 _mark_row_style() 手动控制。
        self.table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        # 空间不够时才显示横向滚动条
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        # 去除 Qt 默认焦点轮廓；
        # 表头字体加粗。
        self.table.setStyleSheet("""
            QTableWidget {
                outline: none;
            }

            QHeaderView::section {
                font-weight: bold;
            }
        """)

        header = self.table.horizontalHeader()

        # 不让最后一列单独吞掉所有剩余空间
        header.setStretchLastSection(False)

        # 禁止用户拖动列顺序
        header.setSectionsMovable(False)

        # 禁止表头点击效果
        header.setSectionsClickable(False)

        # 表头字体加粗
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)

        # 隐藏左侧行号
        self.table.verticalHeader().setVisible(False)

        self.table.cellClicked.connect(
            self._on_cell_clicked
        )

    # =========================================================
    # 数据接口
    # =========================================================
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
        if self.data is None or "date" not in self.data:
            self.clear_table()
            return

        dates = self.data["date"]
        row_count = len(dates)
        col_count = 1 + len(keys)

        self.table.blockSignals(True)

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

        self._set_column_width_policy()

        self.table.blockSignals(False)

    def _set_column_width_policy(self):
        """
        设置表格列宽策略。

        所有列统一按当前表格宽度均匀拉伸，
        不再只让最后一列填充剩余空间。
        """

        if self.table.columnCount() <= 0:
            return

        header = self.table.horizontalHeader()

        # 每列均匀拉伸，整体填满表格宽度
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(
                col,
                QHeaderView.Stretch,
            )

        # 防止列宽过窄导致表头和数值挤在一起
        header.setMinimumSectionSize(120)

        # 不让最后一列特殊拉伸
        header.setStretchLastSection(False)

    def get_available_property_keys(self):
        """
        获取当前表格可显示的英文字段 key。
        """
        if self.data is None:
            return []

        ordered = [
            key
            for key in self.property_order
            if key in self.data and key != "date"
        ]

        extra = [
            key
            for key in self.data.keys()
            if key not in ordered and key != "date"
        ]

        return ordered + extra

    def clear_table(self):
        """
        清空表格。
        """
        self.table.blockSignals(True)

        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        self.current_marked_row = None

        self.table.blockSignals(False)

    # =========================================================
    # 表格选中与线图联动
    # =========================================================
    def select_row_by_index(
        self,
        row_index,
        scroll_to_center=True,
    ):
        """
        外部调用：
        根据线图点击的数据点，自动高亮表格对应行。

        参数：
        - row_index：要选中的行号
        - scroll_to_center：
            True  ：线图点击后使用，自动滚动到表格中间
            False ：表格自身点击时使用，不自动滚动

        效果：
        1. 对应行蓝色底
        2. 对应行白色字
        3. 线图点击时自动滚动到表格中间
        """

        try:
            row_index = int(row_index)
        except Exception:
            return

        if row_index < 0:
            return

        if row_index >= self.table.rowCount():
            return

        self.table.blockSignals(True)

        # 先恢复上一行的普通样式
        if self.current_marked_row is not None:
            self._reset_row_style(
                self.current_marked_row
            )

        # 标记当前行
        self.current_marked_row = row_index
        self._mark_row_style(row_index)

        # 仅线图点击时滚动到中间；
        # 用户在表格内点击时不跳动。
        if scroll_to_center:
            first_item = self.table.item(row_index, 0)

            if first_item is not None:
                self.table.scrollToItem(
                    first_item,
                    QAbstractItemView.PositionAtCenter,
                )

        self.table.blockSignals(False)

    def clear_selection(self):
        """
        清除表格选中状态和蓝色标记。
        """

        self.table.blockSignals(True)

        if self.current_marked_row is not None:
            self._reset_row_style(
                self.current_marked_row
            )

        self.current_marked_row = None

        # 虽然当前是 NoSelection，
        # 这里仍保留清除调用，避免以后切回 Qt 选中模式时有残留。
        self.table.clearSelection()

        self.table.blockSignals(False)

    def _mark_row_style(self, row_index):
        """
        把某一行设置为蓝色底、白色字。
        """

        if row_index < 0:
            return

        if row_index >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row_index, col)

            if item is None:
                continue

            item.setBackground(
                QBrush(self.mark_background_color)
            )

            item.setForeground(
                QBrush(self.mark_text_color)
            )

    def _reset_row_style(self, row_index):
        """
        恢复某一行普通样式。
        """

        if row_index < 0:
            return

        if row_index >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row_index, col)

            if item is None:
                continue

            # 恢复 Qt 的默认 / 隔行背景色
            item.setBackground(QBrush())

            item.setForeground(
                QBrush(self.normal_text_color)
            )

    def _on_cell_clicked(self, row, column):
        """
        点击表格任意单元格时：

        1. 点击新行：
           - 高亮当前行；
           - 不自动滚动；
           - 向线图发送当前行号。

        2. 再次点击同一行：
           - 取消蓝色高亮；
           - 向线图发送 -1；
           - 线图可以据此隐藏红色竖直定位线。
        """

        if self.current_marked_row == row:
            self.clear_selection()
            self.row_selected.emit(-1)
            return

        self.select_row_by_index(
            row_index=row,
            scroll_to_center=False,
        )

        self.row_selected.emit(int(row))

    # =========================================================
    # 属性名称与数值格式化
    # =========================================================
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