#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teams課題機能（Education API）検証スクリプト

現在の環境でTeams課題評価機能が使用可能かを確認します。
"""

import sys
import os

# プロジェクトのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.auth import AuthManager
import requests


def check_education_api(auth_manager):
    """Education APIの利用可否を確認"""
    print("="*60)
    print("Teams Education API 検証")
    print("="*60)
    print()
    
    token = auth_manager.get_token()
    if not token:
        print("❌ 認証トークンが取得できませんでした")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 自分のEducationユーザー情報を取得
    print("[1/4] Education ユーザー情報を確認中...")
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/education/me",
            headers=headers
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Education APIにアクセス可能")
            print(f"   ユーザー: {user_data.get('displayName', 'N/A')}")
            print(f"   タイプ: {user_data.get('primaryRole', 'N/A')}")
        elif response.status_code == 403:
            print("❌ Education APIへのアクセス権限がありません")
            print("   詳細:", response.json().get('error', {}).get('message', ''))
            return False
        else:
            print(f"⚠️  予期しないエラー: {response.status_code}")
            print("   詳細:", response.text)
            return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False
    
    print()
    
    # 2. クラス一覧を取得
    print("[2/4] Teamsクラス（教育）を確認中...")
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/education/me/classes",
            headers=headers
        )
        
        if response.status_code == 200:
            classes_data = response.json()
            classes = classes_data.get('value', [])
            
            if len(classes) == 0:
                print("⚠️  Education クラスが見つかりません")
                print("   → Teams課題機能を使用していない可能性があります")
                return False
            
            print(f"✅ {len(classes)}個のEducationクラスを検出")
            for i, cls in enumerate(classes[:5], 1):  # 最大5件表示
                print(f"   {i}. {cls.get('displayName', 'N/A')} (ID: {cls.get('id', 'N/A')[:20]}...)")
            
            if len(classes) > 5:
                print(f"   ... 他{len(classes) - 5}件")
            
            # 最初のクラスで詳細確認
            if classes:
                class_id = classes[0]['id']
                class_name = classes[0].get('displayName', 'N/A')
                
                print()
                print(f"[3/4] サンプルクラス「{class_name}」の課題を確認中...")
                
                # 課題一覧を取得
                response = requests.get(
                    f"https://graph.microsoft.com/v1.0/education/classes/{class_id}/assignments",
                    headers=headers
                )
                
                if response.status_code == 200:
                    assignments_data = response.json()
                    assignments = assignments_data.get('value', [])
                    
                    if len(assignments) == 0:
                        print("⚠️  課題が見つかりません")
                        print("   → Teams課題機能が有効だが、課題が作成されていない")
                    else:
                        print(f"✅ {len(assignments)}個の課題を検出")
                        for i, assignment in enumerate(assignments[:3], 1):  # 最大3件表示
                            print(f"   {i}. {assignment.get('displayName', 'N/A')}")
                        
                        if len(assignments) > 3:
                            print(f"   ... 他{len(assignments) - 3}件")
                        
                        # 最初の課題で提出物を確認
                        if assignments:
                            assignment_id = assignments[0]['id']
                            assignment_name = assignments[0].get('displayName', 'N/A')
                            
                            print()
                            print(f"[4/4] サンプル課題「{assignment_name}」の提出物を確認中...")
                            
                            response = requests.get(
                                f"https://graph.microsoft.com/v1.0/education/classes/{class_id}/assignments/{assignment_id}/submissions",
                                headers=headers
                            )
                            
                            if response.status_code == 200:
                                submissions_data = response.json()
                                submissions = submissions_data.get('value', [])
                                
                                print(f"✅ {len(submissions)}件の提出物を検出")
                                
                                # 提出済みの件数をカウント
                                submitted = [s for s in submissions if s.get('status') == 'submitted' or s.get('status') == 'returned']
                                print(f"   提出済み: {len(submitted)}件")
                                
                                if submitted:
                                    print("\n   サンプル提出物:")
                                    sample = submitted[0]
                                    print(f"   - 学生ID: {sample.get('recipient', {}).get('userId', 'N/A')[:20]}...")
                                    print(f"   - ステータス: {sample.get('status', 'N/A')}")
                                    print(f"   - 提出日時: {sample.get('submittedDateTime', 'N/A')}")
                                
                                return True
                            else:
                                print(f"⚠️  提出物の取得に失敗: {response.status_code}")
                else:
                    print(f"⚠️  課題の取得に失敗: {response.status_code}")
        else:
            print(f"⚠️  クラスの取得に失敗: {response.status_code}")
            print("   詳細:", response.text)
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def check_current_architecture(auth_manager):
    """現在のアーキテクチャ（SharePoint Student Work）を確認"""
    print()
    print("="*60)
    print("現在のアーキテクチャ確認")
    print("="*60)
    print()
    
    # config.jsonから既存のクラス情報を読み込み
    import json
    config_file = os.path.join(os.path.dirname(__file__), 'app', 'config.json')
    
    if not os.path.exists(config_file):
        print("ℹ️  config.json が見つかりません（クラス未登録）")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    classes = config.get('classes', [])
    
    if not classes:
        print("ℹ️  登録されているクラスがありません")
        return
    
    print(f"現在登録されているクラス: {len(classes)}個")
    for cls in classes:
        print(f"  - {cls.get('name', 'N/A')}")
        print(f"    SharePointサイト: {cls.get('site_path', 'N/A')}")
    
    print()
    print("📋 判定:")
    print("   これらのクラスは SharePoint ベースのアーキテクチャです。")
    print("   Teams課題APIとは異なるシステムを使用しています。")


def main():
    print("\n🔍 Teams課題評価機能の利用可否を確認します\n")
    
    # 認証
    print("認証を開始します...")
    auth_manager = AuthManager()
    
    if not auth_manager.authenticate():
        print("\n❌ 認証に失敗しました")
        return
    
    print()
    
    # Education API確認
    education_available = check_education_api(auth_manager)
    
    # 現在のアーキテクチャ確認
    check_current_architecture(auth_manager)
    
    # 結果サマリー
    print()
    print("="*60)
    print("検証結果サマリー")
    print("="*60)
    print()
    
    if education_available:
        print("✅ Teams Education API が利用可能です")
        print("✅ 課題評価返却機能の実装が可能です")
        print()
        print("📌 次のステップ:")
        print("   1. Education APIとSharePoint構造の紐付け設計")
        print("   2. 評価データの入力方法の検討（CSV/Excel等）")
        print("   3. 実装の開始")
    else:
        print("❌ Teams Education API が利用できません")
        print()
        print("考えられる原因:")
        print("   1. アプリ登録に Education スコープが不足")
        print("   2. テナントでEducation機能が無効")
        print("   3. ユーザーアカウントが教育用ライセンスを持っていない")
        print()
        print("📌 対処方法:")
        print("   - Azure AD管理者に Education API の権限追加を依頼")
        print("   - または、SharePointベースの別のアプローチを検討")
    
    print()


if __name__ == "__main__":
    main()
