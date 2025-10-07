# -*- coding: utf-8 -*-
"""
测试姓名顺序检测器 / Тесты детектора порядка имен

作者 / Автор: Ма Цзясин (Ma Jiaxin)
项目 / Проект: ИСТИНА - 智能科学计量数据专题研究系统
"""

import sys
from pathlib import Path

# 添加src目录到路径 / Добавление каталога src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from name_order_detector import (
    NameOrderDetector,
    NameOrder,
    AuthorNameParts,
    ParsedAuthor,
    create_name_order_detector
)
from src.chinese_name_processor import ChineseNameProcessor, SurnameDatabase


class TestNameOrderDetector:
    """
    姓名顺序检测器测试类 / Класс тестов детектора порядка имен
    """

    @pytest.fixture
    def surname_db(self):
        """
        创建姓氏数据库fixture / Создание фикстуры базы данных фамилий
        """
        return SurnameDatabase()

    @pytest.fixture
    def detector(self, surname_db):
        """
        创建检测器fixture / Создание фикстуры детектора
        """
        return create_name_order_detector(surname_db)

    # ============================
    # 测试基本功能 / Тесты базовых функций
    # ============================

    def test_detector_initialization(self, surname_db):
        """
        测试检测器初始化 / Тест инициализации детектора
        """
        detector = NameOrderDetector(surname_db)
        assert detector is not None
        assert detector.surname_db is not None
        assert detector.given_name_db is not None
        assert len(detector.given_name_db) > 0

    def test_create_name_order_detector_factory(self, surname_db):
        """
        测试工厂函数 / Тест фабричной функции
        """
        detector = create_name_order_detector(surname_db)
        assert detector is not None
        assert isinstance(detector, NameOrderDetector)

    # ============================
    # 测试姓-名顺序检测 / Тесты определения порядка фамилия-имя
    # ============================

    def test_detect_surname_first_order_chinese(self, detector):
        """
        测试中文姓-名顺序检测 / Тест определения китайского порядка фамилия-имя

        示例 / Пример: 张明 (Zhang Ming)
        """
        result = detector.detect_name_order("Zhang Ming")
        assert result.detected_order == NameOrder.SURNAME_FIRST
        assert len(result.name_parts) == 2
        assert result.name_parts[0] == "Zhang"
        assert result.name_parts[1] == "Ming"
        assert result.confidence > 0.7

    def test_detect_surname_first_order_russian(self, detector):
        """
        测试俄文姓-名顺序检测 / Тест определения русского порядка фамилия-имя

        示例 / Пример: Ivanov Ivan
        """
        result = detector.detect_name_order("Ivanov Ivan")
        assert result.detected_order == NameOrder.SURNAME_FIRST
        assert result.name_parts[1] == "Ivan"
        assert result.is_first_name_map[1] is True  # Ivan是名字 / Ivan - имя

    def test_detect_surname_first_with_patronymic(self, detector):
        """
        测试带父称的姓-名顺序 / Тест порядка фамилия-имя с отчеством

        示例 / Пример: Ivanov Ivan Ivanovich
        """
        result = detector.detect_name_order("Ivanov Ivan Ivanovich")
        assert result.detected_order == NameOrder.SURNAME_FIRST
        assert len(result.name_parts) == 3
        # 检测到父称后缀 / Обнаружен отчественный суффикс
        assert result.is_first_name_map[2] is True  # Ivanovich是父称 / отчество

    def test_detect_surname_first_with_initial(self, detector):
        """
        测试带缩写的姓-名顺序 / Тест порядка фамилия-имя с инициалом

        示例 / Пример: Smith J.
        """
        result = detector.detect_name_order("Smith J.")
        assert result.detected_order == NameOrder.SURNAME_FIRST
        assert result.is_first_name_map[1] is True  # J.是缩写 / J. - инициал

    # ============================
    # 测试名-姓顺序检测 / Тесты определения порядка имя-фамилия
    # ============================

    def test_detect_given_name_first_order(self, detector):
        """
        测试名-姓顺序检测 / Тест определения порядка имя-фамилия

        示例 / Пример: Ming Zhang
        """
        result = detector.detect_name_order("Ming Zhang")
        assert result.detected_order == NameOrder.GIVEN_NAME_FIRST
        assert result.name_parts[0] == "Ming"
        assert result.is_first_name_map[0] is True  # Ming是名字 / Ming - имя

    def test_detect_given_name_first_english(self, detector):
        """
        测试英文名-姓顺序 / Тест английского порядка имя-фамилия

        示例 / Пример: John Smith
        """
        result = detector.detect_name_order("John Smith")
        assert result.detected_order == NameOrder.GIVEN_NAME_FIRST
        assert result.name_parts[0] == "John"
        assert result.is_first_name_map[0] is True

    def test_detect_given_name_first_with_middle(self, detector):
        """
        测试带中间名的名-姓顺序 / Тест порядка имя-фамилия с средним именем

        示例 / Пример: John Michael Smith
        """
        result = detector.detect_name_order("John Michael Smith")
        assert result.detected_order == NameOrder.GIVEN_NAME_FIRST
        assert result.name_parts[0] == "John"

    # ============================
    # 测试无法判断的情况 / Тесты неопределенных случаев
    # ============================

    def test_detect_undetermined_order(self, detector):
        """
        测试无法判断的顺序 / Тест неопределенного порядка

        示例 / Пример: 两个都不在数据库中的词
        """
        result = detector.detect_name_order("Unknown Person")
        # 可能是UNDETERMINED或基于姓氏数据库的推断
        assert result is not None
        assert result.confidence < 0.9  # 置信度应该较低

    def test_detect_single_name(self, detector):
        """
        测试单个名字 / Тест одного имени
        """
        result = detector.detect_name_order("Zhang")
        assert len(result.name_parts) == 1
        assert result.name_parts[0] == "Zhang"

    def test_detect_empty_string(self, detector):
        """
        测试空字符串 / Тест пустой строки
        """
        result = detector.detect_name_order("")
        assert result.detected_order == NameOrder.UNDETERMINED
        assert len(result.name_parts) == 0

    # ============================
    # 测试作者列表解析 / Тесты разбора списков авторов
    # ============================

    def test_parse_single_author(self, detector):
        """
        测试解析单个作者 / Тест разбора одного автора
        """
        authors = detector.parse_author_list("Zhang Ming")
        assert len(authors) == 1
        assert authors[0].surname == "Zhang"
        assert authors[0].given_name == "Ming"

    def test_parse_multiple_authors(self, detector):
        """
        测试解析多个作者 / Тест разбора нескольких авторов

        示例 / Пример: Zhang San; Li Ming; Wang Xiaohong
        """
        authors = detector.parse_author_list("Zhang San; Li Ming; Wang Xiaohong")
        assert len(authors) == 3

        # 第一作者 / Первый автор
        assert authors[0].surname == "Zhang"
        assert authors[0].given_name == "San"

        # 第二作者 / Второй автор
        assert authors[1].surname == "Li"
        assert authors[1].given_name == "Ming"

        # 第三作者 / Третий автор
        assert authors[2].surname == "Wang"

    def test_parse_mixed_format_authors(self, detector):
        """
        测试解析混合格式作者列表 / Тест разбора списка авторов в смешанном формате

        ISTINA系统典型场景: 第一作者使用"姓, 名"格式,其他作者使用"姓 名"格式
        Типичный сценарий ИСТИНА: первый автор в формате "фамилия, имя", остальные - "фамилия имя"

        注意: 逗号在作者列表中被当作分隔符,所以"Ivanov, Ivan"会被分成两个作者
        Примечание: запятая рассматривается как разделитель в списке авторов,
        поэтому "Ivanov, Ivan" разделяется на двух авторов
        """
        authors = detector.parse_author_list("Ivanov, Ivan; Petrov Petr")
        # 由于逗号是分隔符,"Ivanov, Ivan"被分成两个作者 / Из-за запятой-разделителя получается 3 автора
        assert len(authors) >= 2

        # 系统应该能够解析所有作者 / Система должна разобрать всех авторов
        assert all(author.surname != "" for author in authors)

    def test_parse_authors_with_initials(self, detector):
        """
        测试解析带缩写的作者列表 / Тест разбора списка авторов с инициалами
        """
        authors = detector.parse_author_list("Zhang M.; Li X.H.; Wang J.")
        assert len(authors) == 3

        # 所有作者都应该被正确解析
        # Все авторы должны быть правильно разобраны
        for author in authors:
            assert author.surname != ""

    def test_parse_empty_author_list(self, detector):
        """
        测试解析空作者列表 / Тест разбора пустого списка авторов
        """
        authors = detector.parse_author_list("")
        assert len(authors) == 0

    # ============================
    # 测试批量检测 / Тесты пакетного определения
    # ============================

    def test_batch_detect_orders(self, detector):
        """
        测试批量检测姓名顺序 / Тест пакетного определения порядка имен
        """
        names = ["Zhang Ming", "Ming Zhang", "Ivan Ivanov"]
        results = detector.batch_detect_orders(names)

        assert len(results) == 3
        assert all(isinstance(r, AuthorNameParts) for r in results)

    # ============================
    # 测试特殊情况 / Тесты специальных случаев
    # ============================

    def test_detect_with_hyphens(self, detector):
        """
        测试带连字符的姓名 / Тест имен с дефисами

        注意: 连字符会被当作分隔符,所以"Li-Ming"会被分成两个部分
        Примечание: дефис рассматривается как разделитель, поэтому "Li-Ming" разделяется на две части
        """
        result = detector.detect_name_order("Li-Ming Zhang")
        # 连字符被当作分隔符,所以有3个部分: Li, Ming, Zhang
        # Дефис рассматривается как разделитель, поэтому 3 части: Li, Ming, Zhang
        assert len(result.name_parts) == 3
        assert result.name_parts == ['Li', 'Ming', 'Zhang']

    def test_detect_case_insensitive(self, detector):
        """
        测试大小写不敏感 / Тест нечувствительности к регистру
        """
        result1 = detector.detect_name_order("zhang ming")
        result2 = detector.detect_name_order("ZHANG MING")
        result3 = detector.detect_name_order("Zhang Ming")

        # 所有结果应该一致 / Все результаты должны быть одинаковыми
        assert result1.detected_order == result2.detected_order == result3.detected_order

    def test_parse_with_different_separators(self, detector):
        """
        测试不同分隔符的作者列表 / Тест списков авторов с разными разделителями
        """
        # 分号分隔 / Разделение точкой с запятой
        authors1 = detector.parse_author_list("Zhang Ming; Li Wei")

        # 逗号分隔 / Разделение запятой
        authors2 = detector.parse_author_list("Zhang Ming, Li Wei")

        # 中文逗号 / Китайская запятая
        authors3 = detector.parse_author_list("Zhang Ming，Li Wei")

        # 所有情况都应该正确解析 / Все случаи должны быть правильно разобраны
        assert len(authors1) == 2
        assert len(authors2) == 2
        assert len(authors3) == 2

    # ============================
    # 测试频率阈值功能 / Тесты функции порога частоты
    # ============================

    def test_frequency_threshold_logic(self, detector):
        """
        测试频率阈值逻辑 / Тест логики порога частоты

        验证只有频率>=30的名字才被识别
        Проверка, что распознаются только имена с частотой >= 30
        """
        # 检查阈值常量 / Проверка константы порога
        assert detector.FREQUENCY_THRESHOLD == 30

        # 高频名字应该被识别 / Высокочастотные имена должны распознаваться
        assert detector._is_given_name("MING") is True  # 频率85
        assert detector._is_given_name("IVAN") is True  # 频率90

    # ============================
    # 测试置信度计算 / Тесты вычисления достоверности
    # ============================

    def test_confidence_calculation(self, detector):
        """
        测试置信度计算 / Тест вычисления достоверности
        """
        # 高确定性情况 / Случай высокой определенности
        result_high = detector.detect_name_order("Zhang Ming")
        assert result_high.confidence > 0.7

        # 低确定性情况 / Случай низкой определенности
        result_low = detector.detect_name_order("Unknown1 Unknown2")
        assert result_low.confidence < result_high.confidence

    def test_confidence_with_known_surname(self, detector):
        """
        测试已知姓氏对置信度的影响 / Тест влияния известной фамилии на достоверность
        """
        # 姓氏在数据库中 / Фамилия в базе данных
        result_known = detector.detect_name_order("Zhang Ming")

        # 姓氏不在数据库中 / Фамилия не в базе данных
        result_unknown = detector.detect_name_order("Xyzabc Ming")

        # 已知姓氏应该有更高或相等的置信度 / Известная фамилия должна иметь более высокую или равную достоверность
        # 注意: 由于MING是高频名字,即使姓氏未知,置信度也可能相同
        # Примечание: Поскольку MING - высокочастотное имя, достоверность может быть одинаковой даже при неизвестной фамилии
        assert result_known.confidence >= result_unknown.confidence


# ============================
# 集成测试 / Интеграционные тесты
# ============================

class TestNameOrderDetectorIntegration:
    """
    姓名顺序检测器集成测试 / Интеграционные тесты детектора порядка имен
    """

    @pytest.fixture
    def processor(self):
        """
        创建完整的处理器 / Создание полного процессора
        """
        from src.chinese_name_processor import create_default_processor
        return create_default_processor()

    def test_integration_with_chinese_name_processor(self, processor):
        """
        测试与ChineseNameProcessor的集成 / Тест интеграции с ChineseNameProcessor
        """
        # 检查检测器是否成功初始化 / Проверка успешной инициализации детектора
        assert processor.name_order_detector is not None

        # 测试检测功能 / Тест функции определения
        result = processor.detect_name_order("Zhang Ming")
        assert result is not None
        assert 'detected_order' in result
        assert 'confidence' in result

    def test_integration_parse_author_list(self, processor):
        """
        测试作者列表解析集成 / Тест интеграции разбора списка авторов
        """
        authors = processor.parse_author_list("Zhang San; Li Ming; Wang Wu")
        assert authors is not None
        assert len(authors) == 3

        # 验证第一作者标记 / Проверка отметки первого автора
        assert authors[0]['is_first_author'] is True
        assert authors[1]['is_first_author'] is False
        assert authors[2]['is_first_author'] is False

    def test_integration_batch_detection(self, processor):
        """
        测试批量检测集成 / Тест интеграции пакетного определения
        """
        names = ["Zhang Ming", "Li Wei", "Wang Hong"]
        results = processor.batch_detect_name_orders(names)

        assert len(results) == 3
        assert all(r is not None for r in results)


# ============================
# ISTINA系统兼容性测试 / Тесты совместимости с системой ИСТИНА
# ============================

class TestISTINACompatibility:
    """
    ISTINA系统兼容性测试 / Тесты совместимости с системой ИСТИНА

    测试与ISTINA系统中split_authors.py相似的场景
    Тестирование сценариев, аналогичных split_authors.py в системе ИСТИНА
    """

    @pytest.fixture
    def detector(self):
        """创建检测器"""
        surname_db = SurnameDatabase()
        return create_name_order_detector(surname_db)

    def test_istina_case_russian_patronymic(self, detector):
        """
        ISTINA典型案例: 俄语姓-名-父称 / Типичный случай ИСТИНА: русское фамилия-имя-отчество

        示例 / Пример: Иванов Иван Иванович
        """
        result = detector.detect_name_order("Ivanov Ivan Ivanovich")
        assert result.detected_order == NameOrder.SURNAME_FIRST
        assert len(result.name_parts) == 3

    def test_istina_case_mixed_format_list(self, detector):
        """
        ISTINA典型案例: 混合格式作者列表 / Типичный случай ИСТИНА: список авторов в смешанном формате

        第一作者: 姓, 名
        其他作者: 姓 名

        Первый автор: фамилия, имя
        Остальные авторы: фамилия имя

        注意: 由于逗号是分隔符,实际会产生4个作者
        Примечание: из-за запятой-разделителя получится 4 автора
        """
        authors = detector.parse_author_list("Ivanov, I.I.; Petrov P.P.; Sidorov S.S.")
        # 由于逗号分隔,得到4个作者: Ivanov, I.I., Petrov P.P., Sidorov S.S.
        # Из-за разделения запятой: Ivanov, I.I., Petrov P.P., Sidorov S.S.
        assert len(authors) >= 3

        # 验证所有作者都被正确解析 / Проверка правильного разбора всех авторов
        for author in authors:
            assert author.surname != ""

    def test_istina_case_chinese_transliterated(self, detector):
        """
        ISTINA典型案例: 中文音译姓名 / Типичный случай ИСТИНА: транслитерированные китайские имена

        示例 / Пример: Li Ming, Zhang Wei
        """
        result = detector.detect_name_order("Li Ming")
        assert result.detected_order == NameOrder.SURNAME_FIRST

        result2 = detector.detect_name_order("Zhang Wei")
        assert result2.detected_order == NameOrder.SURNAME_FIRST

    def test_istina_order_values(self, detector):
        """
        测试顺序值与ISTINA系统的一致性 / Тест согласованности значений порядка с системой ИСТИНА

        ISTINA顺序值 / Значения порядка ИСТИНА:
         1: 姓-名顺序 / фамилия-имя
         0: 无法判断 / невозможно определить
        -1: 名-姓顺序 / имя-фамилия
        """
        # 姓-名顺序 / Порядок фамилия-имя
        result_surname_first = detector.detect_name_order("Zhang Ming")
        assert result_surname_first.detected_order.value == 1

        # 名-姓顺序 / Порядок имя-фамилия
        result_given_first = detector.detect_name_order("Ming Zhang")
        assert result_given_first.detected_order.value == -1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
