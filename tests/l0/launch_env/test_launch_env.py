from project_manager.l0.launch_env import LaunchEnv


def test_save_and_read_back_in_ignored_folder(tmp_path):
    env = LaunchEnv(tmp_path)
    assert env.command() == ''
    env.save('  conda activate   py314 \n')
    assert env.command() == 'conda activate py314'
    assert (tmp_path / '.overseer' / '.gitignore').read_text(encoding='utf-8') == '*\n'
    # 다른 인스턴스도 같은 값을 읽는다
    assert LaunchEnv(tmp_path).command() == 'conda activate py314'


def test_empty_removes_and_broken_file_reads_empty(tmp_path):
    env = LaunchEnv(tmp_path)
    env.save('conda activate py314')
    env.save('   ')
    assert not env.path.exists()
    env.save('')
    env.root.mkdir(exist_ok=True)
    env.path.write_text('not json', encoding='utf-8')
    assert env.command() == ''
    env.path.write_text('[]', encoding='utf-8')
    assert env.command() == ''
