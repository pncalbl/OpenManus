#!/usr/bin/env python
"""
端到端测试：测试历史功能的实际使用
不依赖完整的 agent 系统
"""

import sys
from pathlib import Path
from datetime import datetime

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from app.history import get_history_manager
from app.schema import Memory, Message


def test_create_and_save_session():
    """测试创建和保存会话"""
    print("\n" + "="*60)
    print("测试 1: 创建和保存会话")
    print("="*60)

    try:
        # 获取 history manager
        manager = get_history_manager()

        # 创建会话
        session_id = manager.create_session(
            agent_name="TestAgent",
            agent_type="TestType",
            workspace_path="./workspace"
        )
        print(f"[OK] 创建会话成功: {session_id}")

        # 创建测试消息
        memory = Memory()
        memory.add_message(Message.user_message("你好，这是测试消息"))
        memory.add_message(Message.assistant_message("收到！这是回复"))
        memory.add_message(Message.user_message("请帮我分析数据"))
        memory.add_message(Message.assistant_message("好的，我来帮你分析"))

        # 保存会话
        success = manager.save_session(
            session_id=session_id,
            memory=memory,
            agent_name="TestAgent",
            agent_type="TestType",
            workspace_path="./workspace"
        )

        if success:
            print(f"[OK] 会话保存成功")
            return session_id
        else:
            print("[FAIL] 会话保存失败 - save_session 返回 False")
            return None

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_list_sessions():
    """测试列出会话"""
    print("\n" + "="*60)
    print("测试 2: 列出所有会话")
    print("="*60)

    try:
        manager = get_history_manager()
        sessions = manager.list_sessions()

        print(f"[OK] 找到 {len(sessions)} 个会话")

        for session in sessions:
            print(f"  - {session.session_id}")
            print(f"    Agent: {session.agent_name}")
            print(f"    消息数: {session.message_count}")
            print(f"    创建时间: {session.created_at}")

        return len(sessions) > 0

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_session(session_id):
    """测试加载会话"""
    print("\n" + "="*60)
    print("测试 3: 加载会话")
    print("="*60)

    try:
        manager = get_history_manager()
        loaded_memory = manager.load_session(session_id)

        if loaded_memory:
            print(f"[OK] 会话加载成功")
            print(f"[OK] 消息数量: {len(loaded_memory.messages)}")

            # 显示前两条消息
            for i, msg in enumerate(loaded_memory.messages[:2]):
                print(f"  消息 {i+1}: [{msg.role}] {msg.content}")

            return True
        else:
            print(f"[FAIL] 会话加载失败")
            return False

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_session(session_id):
    """测试删除会话"""
    print("\n" + "="*60)
    print("测试 4: 删除会话")
    print("="*60)

    try:
        manager = get_history_manager()
        success = manager.delete_session(session_id)

        if success:
            print(f"[OK] 会话删除成功: {session_id}")

            # 验证删除
            sessions = manager.list_sessions()
            still_exists = any(s.session_id == session_id for s in sessions)

            if not still_exists:
                print(f"[OK] 确认会话已删除")
                return True
            else:
                print(f"[FAIL] 会话仍然存在")
                return False
        else:
            print(f"[FAIL] 会话删除失败")
            return False

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有端到端测试"""
    print("="*60)
    print("历史功能端到端测试")
    print("="*60)

    results = []

    # 测试 1: 创建和保存
    session_id = test_create_and_save_session()
    results.append(("创建和保存会话", session_id is not None))

    if session_id:
        # 测试 2: 列出会话
        list_success = test_list_sessions()
        results.append(("列出会话", list_success))

        # 测试 3: 加载会话
        load_success = test_load_session(session_id)
        results.append(("加载会话", load_success))

        # 测试 4: 删除会话
        delete_success = test_delete_session(session_id)
        results.append(("删除会话", delete_success))

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
