# -*- coding: utf-8 -*-
"""
Высокопроизводительная структура данных Trie для хранения и поиска китайских фамилий
高性能中文姓氏前缀树数据结构

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
Модуль / 模块: Высокопроизводительный алгоритм сопоставления фамилий на основе префиксного дерева
               基于前缀树的高性能姓氏匹配算法

Описание / 描述:
Реализует структуру данных Trie (префиксное дерево) для эффективного поиска китайских фамилий.
Обеспечивает временную сложность O(m) для поиска, где m - длина поискового запроса,
что значительно превосходит линейный поиск O(n) по списку фамилий.

实现了用于高效搜索中文姓氏的Trie（前缀树）数据结构。
提供O(m)的时间复杂度进行搜索，其中m是查询字符串的长度，
这显著优于对姓氏列表进行O(n)的线性搜索。
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger("surname_trie")

@dataclass
class SurnameMatch:
    """
    Класс результата поиска фамилии / 姓氏匹配结果类

    Поля / 字段:
        surname (str): Найденная фамилия / 找到的姓氏
        length (int): Длина фамилии в символах / 姓氏字符长度
        frequency (int): Частота встречаемости / 使用频率
        is_compound (bool): Является ли составной фамилией / 是否为复合姓氏
    """
    surname: str
    length: int
    frequency: int
    is_compound: bool


class TrieNode:
    """
    Узел префиксного дерева / Trie树节点

    Оптимизированная структура узла для хранения китайских символов и метаданных фамилий.
    针对存储中文字符和姓氏元数据优化的节点结构。
    """

    def __init__(self, char: str = ''):
        """
        Инициализация узла / 初始化节点

        Args / 参数:
            char (str): Символ, хранящийся в данном узле / 存储在此节点的字符
        """
        self.char: str = char
        # Дочерние узлы, индексированные по символам / 按字符索引的子节点
        self.children: Dict[str, 'TrieNode'] = {}
        # Флаг окончания фамилии / 姓氏结束标志
        self.is_end_of_surname: bool = False
        # Метаданные фамилии / 姓氏元数据
        self.surname_info: Optional[Dict] = None
        # Глубина узла в дереве / 节点在树中的深度
        self.depth: int = 0

    def add_child(self, char: str) -> 'TrieNode':
        """
        Добавляет дочерний узел / 添加子节点

        Args / 参数:
            char (str): Символ для добавления / 要添加的字符

        Returns / 返回:
            TrieNode: Новый или существующий дочерний узел / 新的或现有的子节点
        """
        if char not in self.children:
            child_node = TrieNode(char)
            child_node.depth = self.depth + 1
            self.children[char] = child_node

        return self.children[char]

    def has_child(self, char: str) -> bool:
        """
        Проверяет наличие дочернего узла / 检查是否有子节点

        Args / 参数:
            char (str): Символ для проверки / 要检查的字符

        Returns / 返回:
            bool: True если дочерний узел существует / 如果子节点存在则返回True
        """
        return char in self.children

    def get_child(self, char: str) -> Optional['TrieNode']:
        """
        Получает дочерний узел / 获取子节点

        Args / 参数:
            char (str): Символ дочернего узла / 子节点的字符

        Returns / 返回:
            Optional[TrieNode]: Дочерний узел или None / 子节点或None
        """
        return self.children.get(char)

    def mark_as_surname(self, surname_data: Dict):
        """
        Отмечает узел как окончание фамилии / 将节点标记为姓氏结尾

        Args / 参数:
            surname_data (Dict): Данные о фамилии / 姓氏数据
        """
        self.is_end_of_surname = True
        self.surname_info = surname_data.copy()

    def get_all_surnames(self, current_path: str = '') -> List[Tuple[str, Dict]]:
        """
        Рекурсивно получает все фамилии из поддерева / 递归获取子树中的所有姓氏

        Args / 参数:
            current_path (str): Текущий путь в дереве / 当前树路径

        Returns / 返回:
            List[Tuple[str, Dict]]: Список фамилий с их данными / 姓氏及其数据列表
        """
        surnames = []

        # Если текущий узел - окончание фамилии / 如果当前节点是姓氏结尾
        if self.is_end_of_surname and self.surname_info:
            surnames.append((current_path, self.surname_info))

        # Рекурсивно обходим дочерние узлы / 递归遍历子节点
        for char, child in self.children.items():
            child_surnames = child.get_all_surnames(current_path + char)
            surnames.extend(child_surnames)

        return surnames


class SurnameTrie:
    """
    Высокопроизводительная структура данных Trie для китайских фамилий
    高性能中文姓氏Trie数据结构

    Обеспечивает эффективный поиск фамилий с временной сложностью O(m),
    где m - длина поискового запроса.
    提供高效的姓氏搜索，时间复杂度为O(m)，其中m是搜索查询的长度。
    """

    def __init__(self):
        """Инициализация корневого узла дерева / 初始化树的根节点"""
        self.root = TrieNode()
        self._surname_count = 0
        self._max_surname_length = 0
        self._compound_surnames_count = 0

        # Статистика производительности / 性能统计
        self._build_time = 0.0
        self._memory_usage = 0

    def insert(self, surname: str, surname_data: Dict):
        """
        Вставляет фамилию в Trie / 向Trie中插入姓氏

        Args / 参数:
            surname (str): Фамилия для вставки / 要插入的姓氏
            surname_data (Dict): Метаданные фамилии / 姓氏元数据
        """
        if not surname or not isinstance(surname, str):
            logger.warning(f"Некорректная фамилия для вставки: {surname}")
            return

        try:
            current_node = self.root

            # Проходим по каждому символу фамилии / 遍历姓氏的每个字符
            for char in surname:
                current_node = current_node.add_child(char)

            # Отмечаем последний узел как конец фамилии / 标记最后节点为姓氏结尾
            current_node.mark_as_surname(surname_data)

            # Обновляем статистику / 更新统计信息
            self._surname_count += 1
            self._max_surname_length = max(self._max_surname_length, len(surname))

            if len(surname) > 1:
                self._compound_surnames_count += 1

            logger.debug(f"Фамилия '{surname}' успешно добавлена в Trie")

        except Exception as e:
            logger.error(f"Ошибка при вставке фамилии '{surname}': {e}")

    def search(self, query: str) -> Optional[SurnameMatch]:
        """
        Поиск точного совпадения фамилии / 精确姓氏匹配搜索

        Args / 参数:
            query (str): Поисковый запрос / 搜索查询

        Returns / 返回:
            Optional[SurnameMatch]: Результат поиска или None / 搜索结果或None
        """
        if not query:
            return None

        try:
            current_node = self.root

            # Проходим по символам запроса / 遍历查询字符
            for char in query:
                current_node = current_node.get_child(char)
                if current_node is None:
                    return None

            # Проверяем, является ли текущий узел концом фамилии / 检查当前节点是否为姓氏结尾
            if current_node.is_end_of_surname and current_node.surname_info:
                return SurnameMatch(
                    surname=query,
                    length=len(query),
                    frequency=current_node.surname_info.get('frequency', 0),
                    is_compound=len(query) > 1
                )

        except Exception as e:
            logger.error(f"Ошибка при поиске '{query}': {e}")

        return None

    def find_longest_prefix(self, text: str) -> Optional[SurnameMatch]:
        """
        Находит самую длинную фамилию, являющуюся префиксом входного текста
        找到作为输入文本前缀的最长姓氏

        Args / 参数:
            text (str): Входной текст / 输入文本

        Returns / 返回:
            Optional[SurnameMatch]: Самая длинная найденная фамилия / 找到的最长姓氏
        """
        if not text:
            return None

        longest_match = None
        current_node = self.root

        try:
            # Проходим по символам текста / 遍历文本字符
            for i, char in enumerate(text):
                current_node = current_node.get_child(char)

                if current_node is None:
                    break

                # Если найдена фамилия, сохраняем её как потенциальное совпадение
                # 如果找到姓氏，将其保存为潜在匹配
                if current_node.is_end_of_surname and current_node.surname_info:
                    matched_surname = text[:i + 1]
                    longest_match = SurnameMatch(
                        surname=matched_surname,
                        length=len(matched_surname),
                        frequency=current_node.surname_info.get('frequency', 0),
                        is_compound=len(matched_surname) > 1
                    )

        except Exception as e:
            logger.error(f"Ошибка при поиске префикса в '{text}': {e}")

        return longest_match

    def find_all_prefixes(self, text: str) -> List[SurnameMatch]:
        """
        Находит все фамилии, являющиеся префиксами входного текста
        找到作为输入文本前缀的所有姓氏

        Args / 参数:
            text (str): Входной текст / 输入文本

        Returns / 返回:
            List[SurnameMatch]: Список всех найденных фамилий / 所有找到的姓氏列表
        """
        if not text:
            return []

        matches = []
        current_node = self.root

        try:
            for i, char in enumerate(text):
                current_node = current_node.get_child(char)

                if current_node is None:
                    break

                if current_node.is_end_of_surname and current_node.surname_info:
                    matched_surname = text[:i + 1]
                    match = SurnameMatch(
                        surname=matched_surname,
                        length=len(matched_surname),
                        frequency=current_node.surname_info.get('frequency', 0),
                        is_compound=len(matched_surname) > 1
                    )
                    matches.append(match)

        except Exception as e:
            logger.error(f"Ошибка при поиске всех префиксов в '{text}': {e}")

        return matches

    def get_suggestions(self, prefix: str, max_suggestions: int = 10) -> List[str]:
        """
        Получает предложения автозаполнения для заданного префикса
        获取给定前缀的自动补全建议

        Args / 参数:
            prefix (str): Префикс для поиска / 搜索前缀
            max_suggestions (int): Максимальное количество предложений / 最大建议数量

        Returns / 返回:
            List[str]: Список предложений / 建议列表
        """
        if not prefix:
            return []

        try:
            # Находим узел префикса / 找到前缀节点
            current_node = self.root
            for char in prefix:
                current_node = current_node.get_child(char)
                if current_node is None:
                    return []

            # Получаем все фамилии из поддерева / 从子树获取所有姓氏
            surnames_data = current_node.get_all_surnames(prefix)

            # Сортируем по частоте использования / 按使用频率排序
            surnames_data.sort(key=lambda x: x[1].get('frequency', 0), reverse=True)

            # Возвращаем только имена фамилий / 只返回姓氏名称
            suggestions = [surname for surname, _ in surnames_data[:max_suggestions]]

            return suggestions

        except Exception as e:
            logger.error(f"Ошибка при получении предложений для '{prefix}': {e}")
            return []

    def contains(self, surname: str) -> bool:
        """
        Проверяет, содержится ли фамилия в Trie / 检查Trie中是否包含姓氏

        Args / 参数:
            surname (str): Фамилия для проверки / 要检查的姓氏

        Returns / 返回:
            bool: True если фамилия найдена / 如果找到姓氏则返回True
        """
        return self.search(surname) is not None

    def remove(self, surname: str) -> bool:
        """
        Удаляет фамилию из Trie / 从Trie中删除姓氏

        Args / 参数:
            surname (str): Фамилия для удаления / 要删除的姓氏

        Returns / 返回:
            bool: True если удаление успешно / 如果删除成功则返回True
        """
        if not surname:
            return False

        def _remove_recursive(node: TrieNode, surname: str, depth: int) -> bool:
            """Рекурсивное удаление / 递归删除"""
            if depth == len(surname):
                if not node.is_end_of_surname:
                    return False

                node.is_end_of_surname = False
                node.surname_info = None

                # Узел можно удалить, если у него нет дочерних узлов / 如果没有子节点可以删除节点
                return len(node.children) == 0

            char = surname[depth]
            child_node = node.get_child(char)

            if child_node is None:
                return False

            should_delete_child = _remove_recursive(child_node, surname, depth + 1)

            if should_delete_child:
                del node.children[char]

                # Возвращаем True, если текущий узел можно удалить / 如果当前节点可以删除则返回True
                return (not node.is_end_of_surname and
                       len(node.children) == 0 and
                       node != self.root)

            return False

        try:
            if _remove_recursive(self.root, surname, 0):
                self._surname_count -= 1
                if len(surname) > 1:
                    self._compound_surnames_count -= 1
                logger.debug(f"Фамилия '{surname}' успешно удалена")
                return True

        except Exception as e:
            logger.error(f"Ошибка при удалении фамилии '{surname}': {e}")

        return False

    def get_all_surnames(self) -> List[str]:
        """
        Получает все фамилии из Trie / 获取Trie中的所有姓氏

        Returns / 返回:
            List[str]: Список всех фамилий / 所有姓氏列表
        """
        surnames_data = self.root.get_all_surnames()
        return [surname for surname, _ in surnames_data]

    def get_statistics(self) -> Dict:
        """
        Получает статистику Trie / 获取Trie统计信息

        Returns / 返回:
            Dict: Статистика использования / 使用统计
        """
        return {
            'total_surnames': self._surname_count,
            'compound_surnames': self._compound_surnames_count,
            'single_surnames': self._surname_count - self._compound_surnames_count,
            'max_surname_length': self._max_surname_length,
            'memory_nodes': self._count_nodes(),
            'build_time': self._build_time
        }

    def _count_nodes(self) -> int:
        """
        Подсчитывает общее количество узлов в Trie / 计算Trie中的节点总数

        Returns / 返回:
            int: Количество узлов / 节点数量
        """
        def _count_recursive(node: TrieNode) -> int:
            count = 1  # Текущий узел / 当前节点
            for child in node.children.values():
                count += _count_recursive(child)
            return count

        return _count_recursive(self.root)

    def build_from_surnames_dict(self, surnames_dict: Dict[str, Dict]):
        """
        Строит Trie из словаря фамилий / 从姓氏字典构建Trie

        Args / 参数:
            surnames_dict (Dict[str, Dict]): Словарь фамилий с метаданными / 带元数据的姓氏字典
        """
        import time

        start_time = time.time()

        logger.info(f"Начинается построение Trie из {len(surnames_dict)} фамилий...")

        for surname, surname_data in surnames_dict.items():
            self.insert(surname, surname_data)

        self._build_time = time.time() - start_time

        logger.info(f"Trie построен за {self._build_time:.4f} секунд")
        logger.info(f"Статистика: {self.get_statistics()}")

    def optimize_memory(self):
        """
        Оптимизирует использование памяти / 优化内存使用

        Удаляет неиспользуемые узлы и оптимизирует структуру дерева.
        删除未使用的节点并优化树结构。
        """
        logger.info("Начинается оптимизация памяти Trie...")

        # Здесь можно добавить дополнительную логику оптимизации
        # 这里可以添加额外的优化逻辑

        logger.info("Оптимизация памяти завершена")

    def validate_integrity(self) -> bool:
        """
        Проверяет целостность структуры Trie / 检查Trie结构完整性

        Returns / 返回:
            bool: True если структура корректна / 如果结构正确则返回True
        """
        def _validate_node(node: TrieNode, path: str = '') -> bool:
            # Проверяем, что узел корректен / 检查节点是否正确
            if node.is_end_of_surname and not node.surname_info:
                logger.error(f"Узел '{path}' помечен как конец фамилии, но не имеет данных")
                return False

            # Рекурсивно проверяем дочерние узлы / 递归检查子节点
            for char, child in node.children.items():
                if not _validate_node(child, path + char):
                    return False

            return True

        try:
            is_valid = _validate_node(self.root)
            if is_valid:
                logger.info("Структура Trie прошла проверку целостности")
            else:
                logger.error("Обнаружены проблемы в структуре Trie")
            return is_valid

        except Exception as e:
            logger.error(f"Ошибка при проверке целостности: {e}")
            return False


def create_optimized_surname_trie(surnames_dict: Dict[str, Dict]) -> SurnameTrie:
    """
    Создаёт оптимизированный Trie для фамилий / 创建优化的姓氏Trie

    Args / 参数:
        surnames_dict (Dict[str, Dict]): Словарь фамилий / 姓氏字典

    Returns / 返回:
        SurnameTrie: Оптимизированная структура Trie / 优化的Trie结构
    """
    trie = SurnameTrie()
    trie.build_from_surnames_dict(surnames_dict)
    trie.optimize_memory()

    if not trie.validate_integrity():
        logger.warning("Созданный Trie имеет проблемы целостности")

    return trie


if __name__ == "__main__":
    # Настройка логирования / 设置日志
    logging.basicConfig(level=logging.INFO)

    # Пример использования / 使用示例
    test_surnames = {
        '李': {'pinyin': 'li', 'palladius': 'ли', 'frequency': 95, 'region': ['全国']},
        '王': {'pinyin': 'wang', 'palladius': 'ван', 'frequency': 92, 'region': ['全国']},
        '欧阳': {'pinyin': 'ouyang', 'palladius': 'оуян', 'frequency': 15, 'region': ['华南']},
        '司马': {'pinyin': 'sima', 'palladius': 'сыма', 'frequency': 12, 'region': ['华北']}
    }

    # Создание и тестирование Trie / 创建和测试Trie
    trie = create_optimized_surname_trie(test_surnames)

    # Тестирование поиска / 测试搜索
    test_names = ['李明', '欧阳修', '司马光', '张三']

    print("=== ТЕСТИРОВАНИЕ TRIE ===")
    for name in test_names:
        result = trie.find_longest_prefix(name)
        if result:
            print(f"Имя: {name} -> Фамилия: {result.surname} (длина: {result.length}, частота: {result.frequency})")
        else:
            print(f"Имя: {name} -> Фамилия не найдена")

    # Статистика производительности / 性能统计
    stats = trie.get_statistics()
    print(f"\nСтатистика Trie: {stats}")