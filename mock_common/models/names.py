#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Имитационный модуль common.models.names, предоставляющий класс Firstname, необходимый для тестирования
"""

class Firstname:
    """Имитационный класс Firstname для тестирования"""
    
    def __init__(self, name, people_count=100):
        self.name = name
        self.people_count = people_count
    
    @classmethod
    def objects(cls):
        """Возвращает менеджер объектов"""
        return FirstnameManager()

class FirstnameManager:
    """Имитационный менеджер объектов для метода in_bulk"""
    
    def in_bulk(self, names):
        """Имитирует метод in_bulk, возвращает словарь имен и их объектов"""
        return {name: Firstname(name) for name in names} 