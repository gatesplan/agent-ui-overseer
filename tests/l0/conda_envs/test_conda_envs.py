from project_manager.l0.conda_envs import CondaEnvs


def env_dir(path):
    (path / 'conda-meta').mkdir(parents=True)
    return path


def test_lists_envs_by_name_without_base_or_missing(tmp_path):
    base = env_dir(tmp_path / 'miniconda3')
    py312 = env_dir(base / 'envs' / 'py312')
    py314 = env_dir(tmp_path / 'user' / 'envs' / 'py314')
    gone = tmp_path / 'other' / 'envs' / 'gone'
    listing = tmp_path / 'environments.txt'
    listing.write_text('\n'.join(map(str, [base, py314, py312, gone, py312, ''])) + '\n', encoding='utf-8')
    assert CondaEnvs(listing).list() == [
        {'name': 'py312', 'prefix': str(py312), 'activate': 'conda activate py312'},
        {'name': 'py314', 'prefix': str(py314), 'activate': 'conda activate py314'},
    ]


def test_same_name_in_two_places_activates_by_path(tmp_path):
    a = env_dir(tmp_path / 'a' / 'envs' / 'work')
    b = env_dir(tmp_path / 'b' / 'envs' / 'work')
    listing = tmp_path / 'environments.txt'
    listing.write_text(f'{a}\n{b}\n', encoding='utf-8')
    assert [e['activate'] for e in CondaEnvs(listing).list()] == [f'conda activate {a}', f'conda activate {b}']


def test_no_conda_gives_empty_list(tmp_path):
    assert CondaEnvs(tmp_path / 'none.txt').list() == []
