# -*- coding: utf-8 -*-
"""
测试结果本地化模块 / Модуль локализации результатов тестов
Localization Module for Test Results

用于将测试输出翻译为中文、俄语、英语
Для перевода выходных данных тестов на китайский, русский, английский языки
For translating test outputs to Chinese, Russian, English

中文注释：多语言支持模块
Русский комментарий: Модуль многоязычной поддержки
"""


class TestResultLocalizer:
    """
    测试结果本地化类 / Класс локализации результатов тестов

    支持三种语言的测试结果本地化：中文、俄语、英语
    Поддержка локализации результатов тестов на трех языках: китайский, русский, английский
    Supports test result localization in three languages: Chinese, Russian, English
    """

    # 翻译字典 / Словарь переводов / Translation dictionary
    TRANSLATIONS = {
        'zh': {
            # 通用术语 / Общие термины / General terms
            'accuracy': '准确率',
            'total_tests': '总测试数',
            'total': '总计',
            'passed': '通过',
            'failed': '失败',
            'processing_speed': '处理速度',
            'result': '结果',
            'progress': '进度',
            'loading': '加载中',
            'loading_data': '加载数据',
            'saving_results': '保存结果',
            'test_complete': '测试完成',
            'results_saved_to': '结果已保存到',

            # 数据集相关 / Датасет / Dataset
            'dataset': '数据集',
            'source': '数据源',
            'total_authors': '总作者数',
            'chinese_authors': '中文作者',
            'non_chinese_authors': '非中文作者',
            'sample_size': '采样大小',

            # 测试相关 / Тестирование / Testing
            'testing_algorithm': '测试算法',
            'running_filter': '运行筛选',
            'validation': '验证',
            'quality_check': '质量检查',
            'false_positive_rate': '误判率',
            'false_positives': '误判',
            'wrongly_excluded': '误排除',
            'exclusion_rate': '排除率',

            # 版本对比 / Сравнение версий / Version comparison
            'version_comparison': '版本对比',
            'better_version': '更优版本',
            'improvement': '改进',
            'difference': '差异',
            'added': '新增',
            'removed': '移除',
            'quantitative_difference': '数量差异',
            'quality_difference': '质量差异',

            # 性能指标 / Метрики производительности / Performance metrics
            'performance': '性能',
            'performance_report': '性能报告',
            'comprehensive_test': '综合测试',
            'final_report': '最终报告',
            'recommendation': '建议',
            'key_findings': '关键发现',
            'summary': '总结',

            # 状态 / Статус / Status
            'excellent': '优秀',
            'good': '良好',
            'needs_improvement': '需改进',
            'acceptable': '可接受',
            'completed': '已完成',
            'in_progress': '进行中',

            # 步骤 / Шаги / Steps
            'step': '步骤',
            'step_1': '步骤1',
            'step_2': '步骤2',
            'step_3': '步骤3',
            'step_4': '步骤4',
            'step_5': '步骤5',
            'step_6': '步骤6',

            # 错误和问题 / Ошибки и проблемы / Errors and issues
            'error': '错误',
            'warning': '警告',
            'issues_found': '发现问题',
            'no_issues': '未发现问题',
        },

        'ru': {
            # 通用术语 / Общие термины / General terms
            'accuracy': 'Точность',
            'total_tests': 'Всего тестов',
            'total': 'Всего',
            'passed': 'Пройдено',
            'failed': 'Провалено',
            'processing_speed': 'Скорость обработки',
            'result': 'Результат',
            'progress': 'Прогресс',
            'loading': 'Загрузка',
            'loading_data': 'Загрузка данных',
            'saving_results': 'Сохранение результатов',
            'test_complete': 'Тестирование завершено',
            'results_saved_to': 'Результаты сохранены в',

            # 数据集相关 / Датасет / Dataset
            'dataset': 'Датасет',
            'source': 'Источник',
            'total_authors': 'Всего авторов',
            'chinese_authors': 'Китайские авторы',
            'non_chinese_authors': 'Не-китайские авторы',
            'sample_size': 'Размер выборки',

            # 测试相关 / Тестирование / Testing
            'testing_algorithm': 'Тестирование алгоритма',
            'running_filter': 'Выполнение фильтрации',
            'validation': 'Валидация',
            'quality_check': 'Проверка качества',
            'false_positive_rate': 'Уровень ложных срабатываний',
            'false_positives': 'Ложные срабатывания',
            'wrongly_excluded': 'Ошибочно исключено',
            'exclusion_rate': 'Уровень исключения',

            # 版本对比 / Сравнение версий / Version comparison
            'version_comparison': 'Сравнение версий',
            'better_version': 'Лучшая версия',
            'improvement': 'Улучшение',
            'difference': 'Различие',
            'added': 'Добавлено',
            'removed': 'Удалено',
            'quantitative_difference': 'Количественное различие',
            'quality_difference': 'Качественное различие',

            # 性能指标 / Метрики производительности / Performance metrics
            'performance': 'Производительность',
            'performance_report': 'Отчет о производительности',
            'comprehensive_test': 'Комплексное тестирование',
            'final_report': 'Финальный отчет',
            'recommendation': 'Рекомендация',
            'key_findings': 'Ключевые выводы',
            'summary': 'Резюме',

            # 状态 / Статус / Status
            'excellent': 'Отлично',
            'good': 'Хорошо',
            'needs_improvement': 'Требует улучшения',
            'acceptable': 'Приемлемо',
            'completed': 'Завершено',
            'in_progress': 'В процессе',

            # 步骤 / Шаги / Steps
            'step': 'Шаг',
            'step_1': 'Шаг 1',
            'step_2': 'Шаг 2',
            'step_3': 'Шаг 3',
            'step_4': 'Шаг 4',
            'step_5': 'Шаг 5',
            'step_6': 'Шаг 6',

            # 错误和问题 / Ошибки и проблемы / Errors and issues
            'error': 'Ошибка',
            'warning': 'Предупреждение',
            'issues_found': 'Обнаружены проблемы',
            'no_issues': 'Проблем не обнаружено',
        },

        'en': {
            # 通用术语 / Общие термины / General terms
            'accuracy': 'Accuracy',
            'total_tests': 'Total Tests',
            'total': 'Total',
            'passed': 'Passed',
            'failed': 'Failed',
            'processing_speed': 'Processing Speed',
            'result': 'Result',
            'progress': 'Progress',
            'loading': 'Loading',
            'loading_data': 'Loading data',
            'saving_results': 'Saving results',
            'test_complete': 'Test completed',
            'results_saved_to': 'Results saved to',

            # 数据集相关 / Датасет / Dataset
            'dataset': 'Dataset',
            'source': 'Source',
            'total_authors': 'Total Authors',
            'chinese_authors': 'Chinese Authors',
            'non_chinese_authors': 'Non-Chinese Authors',
            'sample_size': 'Sample Size',

            # 测试相关 / Тестирование / Testing
            'testing_algorithm': 'Testing Algorithm',
            'running_filter': 'Running Filter',
            'validation': 'Validation',
            'quality_check': 'Quality Check',
            'false_positive_rate': 'False Positive Rate',
            'false_positives': 'False Positives',
            'wrongly_excluded': 'Wrongly Excluded',
            'exclusion_rate': 'Exclusion Rate',

            # 版本对比 / Сравнение версий / Version comparison
            'version_comparison': 'Version Comparison',
            'better_version': 'Better Version',
            'improvement': 'Improvement',
            'difference': 'Difference',
            'added': 'Added',
            'removed': 'Removed',
            'quantitative_difference': 'Quantitative Difference',
            'quality_difference': 'Quality Difference',

            # 性能指标 / Метрики производительности / Performance metrics
            'performance': 'Performance',
            'performance_report': 'Performance Report',
            'comprehensive_test': 'Comprehensive Test',
            'final_report': 'Final Report',
            'recommendation': 'Recommendation',
            'key_findings': 'Key Findings',
            'summary': 'Summary',

            # 状态 / Статус / Status
            'excellent': 'Excellent',
            'good': 'Good',
            'needs_improvement': 'Needs Improvement',
            'acceptable': 'Acceptable',
            'completed': 'Completed',
            'in_progress': 'In Progress',

            # 步骤 / Шаги / Steps
            'step': 'Step',
            'step_1': 'Step 1',
            'step_2': 'Step 2',
            'step_3': 'Step 3',
            'step_4': 'Step 4',
            'step_5': 'Step 5',
            'step_6': 'Step 6',

            # 错误和问题 / Ошибки и проблемы / Errors and issues
            'error': 'Error',
            'warning': 'Warning',
            'issues_found': 'Issues Found',
            'no_issues': 'No Issues',
        }
    }

    def __init__(self, language='ru'):
        """
        初始化本地化器 / Инициализация локализатора / Initialize localizer

        参数 / Параметры / Parameters:
            language: 语言代码 ('zh', 'ru', 'en') / Код языка / Language code
                     默认俄语 / По умолчанию русский / Default Russian
        """
        if language not in self.TRANSLATIONS:
            raise ValueError(f"Unsupported language: {language}. Use 'zh', 'ru', or 'en'")
        self.language = language

    def get_text(self, key):
        """
        获取翻译文本 / Получение переведенного текста / Get translated text

        参数 / Параметры / Parameters:
            key: 文本键 / Ключ текста / Text key

        返回 / Возвращает / Returns:
            翻译后的文本，如果键不存在则返回键本身
            Переведенный текст, или сам ключ если не найден
            Translated text, or key itself if not found
        """
        return self.TRANSLATIONS.get(self.language, {}).get(key, key)

    def format_result(self, results):
        """
        格式化测试结果为指定语言 / Форматирование результатов на указанном языке
        Format test results in specified language

        参数 / Параметры / Parameters:
            results: 包含结果数据的字典 / Словарь с данными результатов / Dict with result data

        返回 / Возвращает / Returns:
            格式化的结果字典 / Форматированный словарь результатов / Formatted result dict
        """
        formatted = {}

        key_mappings = {
            'accuracy': 'accuracy',
            'total': 'total_tests',
            'passed': 'passed',
            'failed': 'failed',
            'chinese_count': 'chinese_authors',
            'non_chinese_count': 'non_chinese_authors',
            'false_positive_rate': 'false_positive_rate'
        }

        for orig_key, trans_key in key_mappings.items():
            if orig_key in results:
                formatted[self.get_text(trans_key)] = results[orig_key]

        return formatted

    def get_separator(self, length=80, char='='):
        """
        获取分隔线 / Получение разделительной линии / Get separator line

        参数 / Параметры / Parameters:
            length: 长度 / Длина / Length
            char: 字符 / Символ / Character

        返回 / Возвращает / Returns:
            分隔线字符串 / Строка-разделитель / Separator string
        """
        return char * length

    def get_progress_message(self, current, total):
        """
        获取进度消息 / Получение сообщения о прогрессе / Get progress message

        参数 / Параметры / Parameters:
            current: 当前进度 / Текущий прогресс / Current progress
            total: 总数 / Всего / Total

        返回 / Возвращает / Returns:
            进度消息字符串 / Строка сообщения о прогрессе / Progress message string
        """
        return f"  {self.get_text('progress')}: {current:,}/{total:,}..."


# 便捷函数 / Вспомогательные функции / Helper functions

def get_localizer(language='ru'):
    """
    获取本地化器实例 / Получение экземпляра локализатора / Get localizer instance

    参数 / Параметры / Parameters:
        language: 语言代码 / Код языка / Language code

    返回 / Возвращает / Returns:
        本地化器实例 / Экземпляр локализатора / Localizer instance
    """
    return TestResultLocalizer(language)


def translate(key, language='ru'):
    """
    快速翻译函数 / Функция быстрого перевода / Quick translation function

    参数 / Параметры / Parameters:
        key: 文本键 / Ключ текста / Text key
        language: 语言代码 / Код языка / Language code

    返回 / Возвращает / Returns:
        翻译后的文本 / Переведенный текст / Translated text
    """
    localizer = get_localizer(language)
    return localizer.get_text(key)


# 测试代码 / Тестовый код / Test code
if __name__ == '__main__':
    print("=" * 80)
    print("Localization Module Test / Тест модуля локализации")
    print("=" * 80)

    # 测试三种语言 / Тест трех языков / Test three languages
    for lang in ['zh', 'ru', 'en']:
        print(f"\n### Testing {lang.upper()} ###")
        localizer = get_localizer(lang)

        print(f"{localizer.get_text('accuracy')}: 95.5%")
        print(f"{localizer.get_text('total_authors')}: 410,724")
        print(f"{localizer.get_text('chinese_authors')}: 139,846")
        print(f"{localizer.get_text('false_positive_rate')}: 0.45%")
        print(f"{localizer.get_text('test_complete')}")

    print("\n" + "=" * 80)
    print("Test completed successfully / Тест завершен успешно")
    print("=" * 80)
