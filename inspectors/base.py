from abc import ABC, abstractmethod

class BaseInspector(ABC):
    @abstractmethod
    def inspect(self, image_path, spec):
        """
        spec: 엑셀에서 읽어온 해당 행의 데이터 (Series)
        return: 결과 딕셔너리
        """
        pass