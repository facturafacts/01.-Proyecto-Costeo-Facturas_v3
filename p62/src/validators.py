#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P62 Sales Processing System - Enhanced Validators
Phase 2: Quality System Enhancement

This module provides comprehensive database integrity checks, system diagnostics,
and advanced quality analysis capabilities.
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QualityAnalyzer:
    """Advanced quality analysis and scoring system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.quality_thresholds = {
            'excellent': 98.0,
            'good': 95.0,
            'acceptable': 90.0,
            'poor': 85.0
        }
    
    def calculate_comprehensive_score(self) -> Dict[str, Any]:
        """Calculate comprehensive quality score with detailed breakdown"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get basic counts
                cursor.execute("SELECT COUNT(*) FROM sales_orders")
                orders_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sales_items")
                items_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM quality_logs")
                quality_issues = cursor.fetchone()[0]
                
                total_records = orders_count + items_count
                
                if total_records == 0:
                    return {
                        'overall_score': 0.0,
                        'data_completeness': 0.0,
                        'data_accuracy': 0.0,
                        'data_consistency': 0.0,
                        'reference_integrity': 0.0,
                        'status': 'NO_DATA',
                        'recommendations': ['No data found in database']
                    }
                
                # Data Completeness Score (40% weight)
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_orders 
                    WHERE folio IS NULL OR total IS NULL OR fecha IS NULL
                """)
                incomplete_orders = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_items 
                    WHERE descripcion IS NULL OR cantidad IS NULL OR precio_unitario IS NULL
                """)
                incomplete_items = cursor.fetchone()[0]
                
                completeness_score = ((total_records - incomplete_orders - incomplete_items) / total_records) * 100
                
                # Data Accuracy Score (30% weight)
                accuracy_score = ((total_records - quality_issues) / total_records) * 100
                
                # Data Consistency Score (20% weight)
                cursor.execute("SELECT COUNT(*) FROM sales_orders GROUP BY folio HAVING COUNT(*) > 1")
                duplicate_orders = len(cursor.fetchall())
                
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_items 
                    GROUP BY order_id, descripcion, precio_unitario 
                    HAVING COUNT(*) > 1
                """)
                duplicate_items = len(cursor.fetchall())
                
                consistency_score = 100 - ((duplicate_orders + duplicate_items) / total_records * 100)
                
                # Reference Integrity Score (10% weight)
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_items si 
                    LEFT JOIN sales_orders so ON si.order_id = so.id 
                    WHERE so.id IS NULL
                """)
                orphaned_items = cursor.fetchone()[0]
                
                integrity_score = ((items_count - orphaned_items) / max(items_count, 1)) * 100
                
                # Calculate weighted overall score
                overall_score = (
                    completeness_score * 0.4 +
                    accuracy_score * 0.3 +
                    consistency_score * 0.2 +
                    integrity_score * 0.1
                )
                
                # Determine status
                if overall_score >= self.quality_thresholds['excellent']:
                    status = 'EXCELLENT'
                elif overall_score >= self.quality_thresholds['good']:
                    status = 'GOOD'
                elif overall_score >= self.quality_thresholds['acceptable']:
                    status = 'ACCEPTABLE'
                elif overall_score >= self.quality_thresholds['poor']:
                    status = 'POOR'
                else:
                    status = 'CRITICAL'
                
                # Generate recommendations
                recommendations = self._generate_recommendations(
                    completeness_score, accuracy_score, consistency_score, 
                    integrity_score, duplicate_orders, duplicate_items, orphaned_items
                )
                
                return {
                    'overall_score': round(overall_score, 1),
                    'data_completeness': round(completeness_score, 1),
                    'data_accuracy': round(accuracy_score, 1),
                    'data_consistency': round(consistency_score, 1),
                    'reference_integrity': round(integrity_score, 1),
                    'status': status,
                    'total_records': total_records,
                    'quality_issues': quality_issues,
                    'duplicate_orders': duplicate_orders,
                    'duplicate_items': duplicate_items,
                    'orphaned_items': orphaned_items,
                    'recommendations': recommendations
                }
                
        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            return {
                'overall_score': 0.0,
                'status': 'ERROR',
                'error': str(e),
                'recommendations': ['Unable to perform quality analysis']
            }
    
    def _generate_recommendations(self, completeness: float, accuracy: float, 
                                consistency: float, integrity: float,
                                duplicate_orders: int, duplicate_items: int, 
                                orphaned_items: int) -> List[str]:
        """Generate specific recommendations based on quality metrics"""
        recommendations = []
        
        if completeness < 95:
            recommendations.append("Improve data completeness - check for missing required fields")
        
        if accuracy < 95:
            recommendations.append("Review data validation rules - high number of quality issues detected")
        
        if consistency < 95:
            if duplicate_orders > 0:
                recommendations.append(f"Address {duplicate_orders} duplicate orders")
            if duplicate_items > 0:
                recommendations.append(f"Address {duplicate_items} duplicate items")
        
        if integrity < 95:
            if orphaned_items > 0:
                recommendations.append(f"Fix {orphaned_items} orphaned items without valid orders")
        
        if not recommendations:
            recommendations.append("Quality metrics are excellent - maintain current data practices")
        
        return recommendations

class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            # Database size and file stats
            db_file = Path(self.db_path)
            if not db_file.exists():
                return {'error': 'Database file not found'}
            
            db_size_mb = db_file.stat().st_size / (1024 * 1024)
            last_modified = datetime.fromtimestamp(db_file.stat().st_mtime)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Record counts
                cursor.execute("SELECT COUNT(*) FROM sales_orders")
                orders_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sales_items")
                items_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM quality_logs")
                quality_logs_count = cursor.fetchone()[0]
                
                # Processing time estimates
                cursor.execute("""
                    SELECT MIN(created_at), MAX(created_at) 
                    FROM sales_orders 
                    WHERE created_at IS NOT NULL
                """)
                time_range = cursor.fetchone()
                
                processing_duration = None
                if time_range[0] and time_range[1]:
                    start_time = datetime.fromisoformat(time_range[0])
                    end_time = datetime.fromisoformat(time_range[1])
                    processing_duration = (end_time - start_time).total_seconds()
                
                # Calculate processing speed
                processing_speed = None
                if processing_duration and processing_duration > 0:
                    total_records = orders_count + items_count
                    processing_speed = total_records / processing_duration
                
                # Memory usage estimate (rough calculation)
                estimated_memory_mb = db_size_mb * 2.5  # Assume 2.5x for processing overhead
                
                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_orders 
                    WHERE created_at > datetime('now', '-1 hour')
                """)
                recent_orders = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM quality_logs 
                    WHERE created_at > datetime('now', '-1 hour')
                """)
                recent_issues = cursor.fetchone()[0]
                
                return {
                    'database_size_mb': round(db_size_mb, 2),
                    'last_modified': last_modified.isoformat(),
                    'orders_count': orders_count,
                    'items_count': items_count,
                    'quality_logs_count': quality_logs_count,
                    'total_records': orders_count + items_count,
                    'processing_duration_seconds': processing_duration,
                    'processing_speed_records_per_second': round(processing_speed, 2) if processing_speed else None,
                    'estimated_memory_usage_mb': round(estimated_memory_mb, 2),
                    'recent_orders_last_hour': recent_orders,
                    'recent_issues_last_hour': recent_issues,
                    'performance_status': self._get_performance_status(db_size_mb, processing_speed, quality_logs_count)
                }
                
        except Exception as e:
            logger.error(f"Performance monitoring failed: {e}")
            return {'error': str(e)}
    
    def _get_performance_status(self, db_size: float, speed: Optional[float], issues: int) -> str:
        """Determine overall performance status"""
        if db_size > 500:  # > 500MB
            return "LARGE_DATABASE"
        elif issues > 1000:
            return "HIGH_ISSUES"
        elif speed and speed < 100:  # < 100 records/second
            return "SLOW_PROCESSING"
        else:
            return "OPTIMAL"

def check_database_integrity() -> Dict[str, Any]:
    """Enhanced database integrity check with detailed analysis"""
    script_dir = Path(__file__).parent.parent
    main_db_path = script_dir.parent / "data" / "database" / "cfdi_system_v4.db"
    
    if not main_db_path.exists():
        return {
            'status': 'missing',
            'issues': ['Database file not found'],
            'recommendations': ['Run database setup']
        }
    
    try:
        analyzer = QualityAnalyzer(str(main_db_path))
        quality_metrics = analyzer.calculate_comprehensive_score()
        
        with sqlite3.connect(str(main_db_path)) as conn:
            cursor = conn.cursor()
            
            # Check table existence
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('sales_orders', 'sales_items', 'quality_logs')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = []
            required_tables = ['sales_orders', 'sales_items', 'quality_logs']
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
            
            # Enhanced integrity checks
            issues = []
            
            if missing_tables:
                issues.extend([f"Missing table: {table}" for table in missing_tables])
            
            # Check for orphaned records
            if 'sales_items' in existing_tables and 'sales_orders' in existing_tables:
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_items si 
                    LEFT JOIN sales_orders so ON si.order_id = so.id 
                    WHERE so.id IS NULL
                """)
                orphaned_items = cursor.fetchone()[0]
                if orphaned_items > 0:
                    issues.append(f"Found {orphaned_items} orphaned items")
            
            # Check for data consistency
            if 'sales_orders' in existing_tables:
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_orders 
                    WHERE folio IS NULL OR folio = ''
                """)
                null_folios = cursor.fetchone()[0]
                if null_folios > 0:
                    issues.append(f"Found {null_folios} orders with NULL/empty folios")
            
            # Determine overall status
            if quality_metrics.get('overall_score', 0) >= 95 and not issues:
                status = 'healthy'
            elif quality_metrics.get('overall_score', 0) >= 85:
                status = 'acceptable'
            else:
                status = 'needs_attention'
            
            return {
                'status': status,
                'issues': issues,
                'quality_score': quality_metrics.get('overall_score', 0),
                'quality_status': quality_metrics.get('status', 'UNKNOWN'),
                'recommendations': quality_metrics.get('recommendations', []),
                'tables_found': existing_tables,
                'missing_tables': missing_tables
            }
            
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")
        return {
            'status': 'error',
            'issues': [f"Integrity check failed: {e}"],
            'recommendations': ['Check database file permissions and structure']
        }

def diagnose_system() -> Dict[str, Any]:
    """Enhanced system diagnostics with comprehensive analysis"""
    script_dir = Path(__file__).parent.parent
    main_db_path = script_dir.parent / "data" / "database" / "cfdi_system_v4.db"
    
    try:
        # Initialize analyzers
        analyzer = QualityAnalyzer(str(main_db_path))
        monitor = PerformanceMonitor(str(main_db_path))
        
        # Get quality metrics
        quality_metrics = analyzer.calculate_comprehensive_score()
        
        # Get performance metrics
        performance_metrics = monitor.get_performance_metrics()
        
        # Get basic database info
        with sqlite3.connect(str(main_db_path)) as conn:
            cursor = conn.cursor()
            
            # Get recent quality issues
            cursor.execute("""
                SELECT issue_type, message, created_at 
                FROM quality_logs 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent_issues = cursor.fetchall()
            
            # File system diagnostics
            inbox_dir = script_dir / "inbox"
            logs_dir = script_dir / "logs"
            
            inbox_files = list(inbox_dir.glob("*")) if inbox_dir.exists() else []
            log_files = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
            
            # Combine all diagnostics
            diagnostics = {
                # Basic counts (backward compatibility)
                'database_size_mb': performance_metrics.get('database_size_mb', 0),
                'orders_count': performance_metrics.get('orders_count', 0),
                'items_count': performance_metrics.get('items_count', 0),
                'quality_logs_count': performance_metrics.get('quality_logs_count', 0),
                'duplicate_orders': quality_metrics.get('duplicate_orders', 0),
                'duplicate_items': quality_metrics.get('duplicate_items', 0),
                'quality_score': quality_metrics.get('overall_score', 0),
                
                # Enhanced quality metrics
                'quality_breakdown': {
                    'data_completeness': quality_metrics.get('data_completeness', 0),
                    'data_accuracy': quality_metrics.get('data_accuracy', 0),
                    'data_consistency': quality_metrics.get('data_consistency', 0),
                    'reference_integrity': quality_metrics.get('reference_integrity', 0)
                },
                
                # Performance metrics
                'performance': {
                    'processing_speed': performance_metrics.get('processing_speed_records_per_second'),
                    'estimated_memory_mb': performance_metrics.get('estimated_memory_usage_mb', 0),
                    'last_modified': performance_metrics.get('last_modified'),
                    'recent_activity': {
                        'orders_last_hour': performance_metrics.get('recent_orders_last_hour', 0),
                        'issues_last_hour': performance_metrics.get('recent_issues_last_hour', 0)
                    }
                },
                
                # System status
                'system_status': {
                    'quality_status': quality_metrics.get('status', 'UNKNOWN'),
                    'performance_status': performance_metrics.get('performance_status', 'UNKNOWN'),
                    'inbox_files': len(inbox_files),
                    'log_files': len(log_files)
                },
                
                # Issues and recommendations
                'quality_issues': [f"{issue[0]}: {issue[1]}" for issue in recent_issues],
                'recommendations': quality_metrics.get('recommendations', []),
                
                # Detailed metrics for advanced analysis
                'detailed_metrics': {
                    'orphaned_items': quality_metrics.get('orphaned_items', 0),
                    'total_records': quality_metrics.get('total_records', 0),
                    'processing_duration': performance_metrics.get('processing_duration_seconds'),
                    'database_health': 'healthy' if quality_metrics.get('overall_score', 0) >= 95 else 'needs_attention'
                }
            }
            
            return diagnostics
            
    except Exception as e:
        logger.error(f"System diagnostics failed: {e}")
        return {
            'error': str(e),
            'database_size_mb': 0,
            'orders_count': 0,
            'items_count': 0,
            'quality_logs_count': 0,
            'duplicate_orders': 0,
            'duplicate_items': 0,
            'quality_score': 0,
            'quality_issues': [f"Diagnostics failed: {e}"],
            'recommendations': ['Check system configuration and database connectivity']
        }

def validate_processing_environment() -> Dict[str, Any]:
    """Validate the processing environment for optimal performance"""
    script_dir = Path(__file__).parent.parent
    
    validation_results = {
        'status': 'healthy',
        'issues': [],
        'recommendations': [],
        'environment_score': 100
    }
    
    try:
        # Check directory structure
        required_dirs = ['inbox', 'logs', 'processed', 'failed']
        for dir_name in required_dirs:
            dir_path = script_dir / dir_name
            if not dir_path.exists():
                validation_results['issues'].append(f"Missing directory: {dir_name}")
                validation_results['environment_score'] -= 10
        
        # Check database accessibility
        main_db_path = script_dir.parent / "data" / "database" / "cfdi_system_v4.db"
        if not main_db_path.exists():
            validation_results['issues'].append("Main database not accessible")
            validation_results['environment_score'] -= 30
        
        # Check log file permissions
        logs_dir = script_dir / "logs"
        if logs_dir.exists():
            try:
                test_log = logs_dir / "test_write.tmp"
                test_log.write_text("test")
                test_log.unlink()
            except Exception:
                validation_results['issues'].append("Log directory not writable")
                validation_results['environment_score'] -= 15
        
        # Check available disk space (rough estimate)
        try:
            import shutil
            free_space_gb = shutil.disk_usage(script_dir).free / (1024**3)
            if free_space_gb < 1:  # Less than 1GB
                validation_results['issues'].append("Low disk space available")
                validation_results['environment_score'] -= 20
        except Exception:
            pass  # Skip disk space check if not available
        
        # Generate recommendations
        if validation_results['environment_score'] < 100:
            validation_results['status'] = 'needs_attention'
            validation_results['recommendations'].extend([
                "Run setup scripts to create missing directories",
                "Check file system permissions",
                "Ensure adequate disk space for processing"
            ])
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return {
            'status': 'error',
            'issues': [f"Environment validation failed: {e}"],
            'recommendations': ['Check system configuration'],
            'environment_score': 0
        }
