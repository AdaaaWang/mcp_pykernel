import os
import asyncio

def ssh_info_init(
    ssh_config: dict,
    host: str,
    username: str, 
    key_path: str
) -> str:
    """
    Initialize SSH connection configuration.
    
    Args:
        host: Host address(e.g. perlmutter.nersc.gov)
        username: SSH username
        key_path: SSH private key path (default ~/.ssh/nersc)
    
    Returns:
        Connection status message
    """
    key_full_path = os.path.expanduser(key_path)
    if not os.path.exists(key_full_path):
        return f"Error: SSH private key {key_full_path} does not exist. Please check the path."
    
    ssh_config.update({
        'host': host,
        'username': username,
        'key_path': key_path
    })
    
    return f"SSH configuration: {username}@{host} (key: {key_path})"


async def run_ssh_command(ssh_config: dict, command: str, timeout: int = 30) -> dict:
    """
    Run a command on the remote server via SSH.
    Please optimize the command to make the number of calls to this tool as few as possible.
    If the system returns an error, please check the command and try again.
    Do not try for more than 5 times, as this will cause the system to become unresponsive.

    Args:
        command: bash command to execute on the remote server, in a string.
        timeout: timeout (seconds), default is 30 seconds
    Returns:
        A dictionary containing the execution result, including success status, exit code, stdout, stderr, and command.
    Raises:
        asyncio.TimeoutError: If the command execution exceeds the specified timeout.
        Exception: For any other errors during command execution.
    """
    if not all([ssh_config['host'], ssh_config['username'], ssh_config['key_path']]):
        return {
            'success': False,
            'error': 'SSH connection not initialized, please first use tool ssh_connect.'
        }
    
    ssh_cmd = [
        'ssh',
        '-l', ssh_config['username'],
        '-i', os.path.expanduser(ssh_config['key_path']),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        ssh_config['host'],
        command+'; exit',
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        return {
            'success': True,
            'exit_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'command': command
        }
        
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': f'timeout:({timeout}sec)',
            'command': command
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'command': command
        }