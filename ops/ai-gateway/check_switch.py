"""Read-only preflight on app host. Prints config differences by NAME, not value."""
import json
import subprocess


def main():
    inspect = json.loads(subprocess.check_output(['docker', 'inspect', 'admirra-backend-1']))[0]
    config = json.loads(subprocess.check_output(['docker', 'compose', 'config', '--format', 'json'], cwd='/root/Admirra'))
    service = config['services']['backend']
    actual = dict(entry.split('=', 1) for entry in inspect['Config']['Env'] if '=' in entry)
    configured = service.get('environment', {})
    changed = sorted(key for key, value in configured.items() if str(value or '') != actual.get(key, ''))
    print(json.dumps({'running_image': inspect['Image'], 'configured_image': service.get('image'),
                      'environment_differences_names_only': changed,
                      'running_provider': actual.get('AI_ASSISTANT_PROVIDER', '(default)'),
                      'running_base': actual.get('OPENROUTER_BASE_URL', '(default)')}))


if __name__ == '__main__':
    main()
