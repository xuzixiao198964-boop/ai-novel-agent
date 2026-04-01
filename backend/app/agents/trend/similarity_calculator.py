# -*- coding: utf-8 -*-
"""
相似度计算器 - 基于Sentence-BERT的文本相似度计算
基于详细设计文档实现
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SimilarityResult:
    """相似度计算结果"""
    text1: str
    text2: str
    similarity: float  # 0-1之间的相似度
    is_similar: bool   # 是否超过阈值
    threshold: float = 0.7
    model_used: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        self.is_similar = self.similarity >= self.threshold


class SentenceBERTSimilarity:
    """基于Sentence-BERT的相似度计算器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = "data/cache/similarity"):
        """
        初始化相似度计算器
        
        Args:
            model_name: 预训练模型名称
            cache_dir: 缓存目录
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型加载标志
        self.model = None
        self.tokenizer = None
        
        # 缓存管理
        self.cache = {}
        self.cache_file = self.cache_dir / "similarity_cache.json"
        self._load_cache()
        
        # 配置
        self.similarity_threshold = 0.7
        self.min_text_length = 10
        self.embedding_dim = 384  # all-MiniLM-L6-v2的维度
        
        logger.info(f"相似度计算器初始化完成，模型: {model_name}")
    
    def _load_model(self):
        """加载Sentence-BERT模型"""
        try:
            # 这里使用sentence-transformers库
            # 在实际部署时需要安装: pip install sentence-transformers
            from sentence_transformers import SentenceTransformer
            
            if self.model is None:
                logger.info(f"正在加载Sentence-BERT模型: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("模型加载完成")
                
        except ImportError:
            logger.warning("sentence-transformers库未安装，使用模拟模式")
            self.model = None
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self.model = None
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        if self.model is None:
            # 模拟模式：返回随机向量
            return np.random.randn(self.embedding_dim)
        
        try:
            # 使用Sentence-BERT获取嵌入向量
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            # 返回零向量作为降级
            return np.zeros(self.embedding_dim)
    
    def calculate_similarity(self, text1: str, text2: str, use_cache: bool = True) -> SimilarityResult:
        """
        计算两个文本的相似度
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            use_cache: 是否使用缓存
            
        Returns:
            相似度计算结果
        """
        # 检查缓存
        cache_key = self._generate_cache_key(text1, text2)
        if use_cache and cache_key in self.cache:
            cached_result = self.cache[cache_key]
            # 检查缓存是否过期（7天）
            cache_time = datetime.fromisoformat(cached_result.get("timestamp", "2000-01-01"))
            if datetime.now() - cache_time < timedelta(days=7):
                return SimilarityResult(
                    text1=text1,
                    text2=text2,
                    similarity=cached_result["similarity"],
                    threshold=self.similarity_threshold,
                    model_used=cached_result.get("model_used", self.model_name)
                )
        
        # 预处理文本
        text1_clean = self._preprocess_text(text1)
        text2_clean = self._preprocess_text(text2)
        
        # 检查文本长度
        if len(text1_clean) < self.min_text_length or len(text2_clean) < self.min_text_length:
            logger.warning(f"文本长度不足: {len(text1_clean)}, {len(text2_clean)}")
            similarity = 0.0 if text1_clean != text2_clean else 1.0
        else:
            # 计算相似度
            similarity = self._compute_cosine_similarity(text1_clean, text2_clean)
        
        # 创建结果
        result = SimilarityResult(
            text1=text1,
            text2=text2,
            similarity=similarity,
            threshold=self.similarity_threshold,
            model_used=self.model_name if self.model else "mock"
        )
        
        # 缓存结果
        if use_cache:
            self.cache[cache_key] = {
                "similarity": similarity,
                "timestamp": result.timestamp.isoformat(),
                "model_used": result.model_used
            }
            self._save_cache()
        
        logger.debug(f"相似度计算: '{text1[:30]}...' vs '{text2[:30]}...' = {similarity:.3f}")
        return result
    
    def batch_calculate_similarity(self, texts1: List[str], texts2: List[str]) -> List[SimilarityResult]:
        """
        批量计算相似度
        
        Args:
            texts1: 第一个文本列表
            texts2: 第二个文本列表
            
        Returns:
            相似度计算结果列表
        """
        if len(texts1) != len(texts2):
            raise ValueError("两个文本列表长度必须相同")
        
        results = []
        for text1, text2 in zip(texts1, texts2):
            result = self.calculate_similarity(text1, text2)
            results.append(result)
        
        return results
    
    def find_similar_texts(self, query_text: str, candidate_texts: List[str], 
                          threshold: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        在候选文本中查找与查询文本相似的文本
        
        Args:
            query_text: 查询文本
            candidate_texts: 候选文本列表
            threshold: 相似度阈值，None时使用默认阈值
            
        Returns:
            相似文本列表（文本, 相似度）
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        similar_texts = []
        
        for candidate in candidate_texts:
            result = self.calculate_similarity(query_text, candidate)
            if result.similarity >= threshold:
                similar_texts.append((candidate, result.similarity))
        
        # 按相似度排序
        similar_texts.sort(key=lambda x: x[1], reverse=True)
        
        return similar_texts
    
    def calculate_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """
        计算文本相似度矩阵
        
        Args:
            texts: 文本列表
            
        Returns:
            相似度矩阵 (n x n)
        """
        n = len(texts)
        matrix = np.zeros((n, n))
        
        # 获取所有文本的嵌入向量
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(self._preprocess_text(text))
            embeddings.append(embedding)
        
        embeddings = np.array(embeddings)
        
        # 计算余弦相似度矩阵
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        matrix = np.dot(normalized, normalized.T)
        
        # 对角线设为1（文本与自身的相似度）
        np.fill_diagonal(matrix, 1.0)
        
        return matrix
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        if not text:
            return ""
        
        # 转换为小写
        text = text.lower()
        
        # 移除多余空格
        text = ' '.join(text.split())
        
        # 这里可以添加更多的预处理步骤
        # 如去除停用词、标点符号标准化等
        
        return text
    
    def _compute_cosine_similarity(self, text1: str, text2: str) -> float:
        """计算余弦相似度"""
        # 确保模型已加载
        if self.model is None:
            self._load_model()
        
        # 获取嵌入向量
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        
        # 计算余弦相似度
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # 确保相似度在0-1范围内
        similarity = max(0.0, min(1.0, similarity))
        
        return similarity
    
    def _generate_cache_key(self, text1: str, text2: str) -> str:
        """生成缓存键"""
        # 使用文本的哈希值作为缓存键
        import hashlib
        
        combined = f"{text1}||{text2}".encode('utf-8')
        hash_obj = hashlib.md5(combined)
        return hash_obj.hexdigest()
    
    def _load_cache(self):
        """加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"加载相似度缓存，共 {len(self.cache)} 条记录")
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """保存缓存"""
        try:
            # 限制缓存大小
            if len(self.cache) > 10000:
                # 保留最近使用的5000条
                sorted_items = sorted(self.cache.items(), 
                                    key=lambda x: x[1].get("timestamp", ""), 
                                    reverse=True)
                self.cache = dict(sorted_items[:5000])
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear_cache(self):
        """清空缓存"""
        self.cache = {}
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            logger.info("相似度缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = len(self.cache)
        
        # 计算缓存命中率（需要记录命中次数）
        hits = sum(1 for item in self.cache.values() if item.get("hits", 0) > 0)
        hit_rate = hits / total if total > 0 else 0
        
        # 计算平均相似度
        similarities = [item.get("similarity", 0) for item in self.cache.values()]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        return {
            "total_entries": total,
            "hit_rate": hit_rate,
            "average_similarity": avg_similarity,
            "cache_file_size": self.cache_file.stat().st_size if self.cache_file.exists() else 0,
            "model_used": self.model_name
        }


class GenreSimilarityAnalyzer:
    """题材相似度分析器"""
    
    def __init__(self, similarity_calculator: SentenceBERTSimilarity = None):
        self.similarity_calculator = similarity_calculator or SentenceBERTSimilarity()
        
        # 标准题材分类
        self.standard_genres = [
            "都市现实", "玄幻奇幻", "科幻未来", "历史军事",
            "游戏竞技", "悬疑灵异", "二次元", "其他"
        ]
        
        # 题材特征词
        self.genre_keywords = {
            "都市现实": ["职场", "商战", "校园", "青春", "家庭", "伦理", "医疗", "法律"],
            "玄幻奇幻": ["修仙", "修真", "魔法", "奇幻", "神话", "传说", "异界", "穿越"],
            "科幻未来": ["科幻", "未来", "星际", "太空", "人工智能", "机器人", "虚拟现实", "时间旅行"],
            "历史军事": ["历史", "军事", "战争", "古代", "王朝", "将军", "士兵", "战术"],
            "游戏竞技": ["游戏", "电竞", "竞技", "比赛", "玩家", "副本", "装备", "技能"],
            "悬疑灵异": ["悬疑", "灵异", "恐怖", "推理", "侦探", "神秘", "超自然", "鬼怪"],
            "二次元": ["动漫", "漫画", "轻小说", "同人", "萌系", "宅", "cosplay", "声优"],
            "其他": ["其他", "综合", "杂类", "未分类"]
        }
    
    def analyze_genre_similarity(self, genre_name: str) -> List[Tuple[str, float]]:
        """
        分析题材与标准分类的相似度
        
        Args:
            genre_name: 题材名称
            
        Returns:
            与标准分类的相似度列表（分类, 相似度）
        """
        results = []
        
        for standard_genre in self.standard_genres:
            # 计算题材名称与标准分类的相似度
            name_similarity = self.similarity_calculator.calculate_similarity(
                genre_name, standard_genre
            ).similarity
            
            # 计算与关键词的相似度
            keyword_similarities = []
            for keyword in self.genre_keywords[standard_genre]:
                keyword_sim = self.similarity_calculator.calculate_similarity(
                    genre_name, keyword
                ).similarity
                keyword_similarities.append(keyword_sim)
            
            # 取最高关键词相似度
            max_keyword_sim = max(keyword_similarities) if keyword_similarities else 0
            
            # 综合相似度（名称相似度权重0.6，关键词相似度权重0.4）
            combined_similarity = name_similarity * 0.6 + max_keyword_sim * 0.4
            
            results.append((standard_genre, combined_similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def classify_genre(self, genre_name: str, threshold: float = 0.7) -> Tuple[str, float]:
        """
        分类题材
        
        Args:
            genre_name: 题材名称
            threshold: 分类阈值
            
        Returns:
            (分类名称, 相似度)
        """
        similarities = self.analyze_genre_similarity(genre_name)
        
        if similarities and similarities[0][1] >= threshold:
            return similarities[0]
        else:
            return ("其他", similarities[0][1] if similarities else 0.0)
    
    def find_similar_genres(self, genre_name: str, genre_list: List[str], 
                           threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        在题材列表中查找相似题材
        
        Args:
            genre_name: 查询题材
            genre_list: 题材列表
            threshold: 相似度阈值
            
        Returns:
            相似题材列表（题材, 相似度）
        """
        similar_genres = []
        
        for genre in genre_list:
            if genre == genre_name:
                continue
                
            similarity = self.similarity_calculator.calculate_similarity(
                genre_name, genre
            ).similarity
            
            if similarity >= threshold:
                similar_genres.append((genre, similarity))
        
        # 按相似度排序
        similar_genres.sort(key=lambda x: x[1], reverse=True)
        
        return similar_genres
    
    def cluster_genres(self, genres: List[str], threshold: float = 0.7) -> List[List[str]]:
        """
        聚类相似题材
        
        Args:
            genres: 题材列表
            threshold: 聚类阈值
            
        Returns:
            聚类结果列表
        """
        if not genres:
            return []
        
        # 计算相似度矩阵
        n = len(genres)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarity = self.similarity_calculator.calculate_similarity(
                        genres[i], genres[j]
                    ).similarity
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
        
        # 使用DBSCAN算法聚类
        from sklearn.cluster import DBSCAN
        
        # 将相似度转换为距离
        distance_matrix = 1 - similarity_matrix
        
        # DBSCAN聚类
        dbscan = DBSCAN(eps=1-threshold, min_samples=1, metric='precomputed')
        labels = dbscan.fit_predict(distance_matrix)
        
        # 构建聚类结果
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(genres[i])
        
        # 转换为列表
        cluster_list = list(clusters.values())
        
        return cluster_list
    
    def get_genre_similarity_report(self, genre_name: str) -> Dict[str, Any]:
        """获取题材相似度分析报告"""
        # 分类结果
        classification, similarity = self.classify_genre(genre_name)
        
        # 与标准分类的相似度
        standard_similarities = self.analyze_genre_similarity(genre_name)
        
        # 与关键词的相似度
        keyword_similarities = {}
        for genre, keywords in self.genre_keywords.items():
            max_sim = 0
            for keyword in keywords:
                sim = self.similarity_calculator.calculate_similarity(
                    genre_name, keyword
                ).similarity
                max_sim = max(max_sim, sim)
            keyword_similarities[genre] = max_sim
        
        return {
            "genre_name": genre_name,
            "classification": classification,
            "classification_similarity": similarity,
            "standard_genre_similarities": [
                {"genre": g, "similarity": s} for g, s in standard_similarities
            ],
            "keyword_similarities": keyword_similarities,
            "is_standard_genre": classification in self.standard_genres,
            "recommendation": self._get_classification_recommendation(classification, similarity)
        }
    
    def _get_classification_recommendation(self, classification: str, similarity: float) -> str:
        """获取分类建议"""
        if similarity >= 0.8:
            return f"强烈推荐分类为 '{classification}' (相似度: {similarity:.2f})"
        elif similarity >= 0.7:
            return f"推荐分类为 '{classification}' (相似度: {similarity:.2f})"
        elif similarity >= 0.6:
            return f"可考虑分类为 '{classification}' (相似度: {similarity:.2f})"
        else:
            return f"建议作为新题材处理，最接近的分类是 '{classification}' (相似度: {similarity:.2f})"