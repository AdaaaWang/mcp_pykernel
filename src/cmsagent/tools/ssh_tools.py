import os
import asyncio
from typing import Literal


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

async def run_ssh_command(ssh_config: dict,command: str, timeout: int = 30) -> dict:

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

async def run_scp_transfer(
    ssh_config: dict,
    local_path: str,
    remote_path: str,
    direction: Literal["upload", "download"] = "upload",
    recursive: bool = False,
    timeout: int = 300
) -> dict:
    
    if not all([ssh_config['host'], ssh_config['username'], ssh_config['key_path']]):
        return {
            'success': False,
            'error': 'SSH connection not initialized, please first use tool ssh_connect.'
        }
    
    scp_cmd = [
        'scp',
        '-i', os.path.expanduser(ssh_config['key_path']),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
    ]
    
    if recursive:
        scp_cmd.append('-r')
    
    remote_location = f"{ssh_config['username']}@{ssh_config['host']}:{remote_path}"
    
    if direction == "upload":
        scp_cmd.extend([local_path, remote_location])
        operation = f"Upload {local_path} -> {remote_location}"
    elif direction == "download":
        scp_cmd.extend([remote_location, local_path])
        operation = f"Download {remote_location} -> {local_path}"
    else:
        return {
            'success': False,
            'error': 'Invalid direction. Must be "upload" or "download".'
        }
    
    try:
        if direction == "upload" and not os.path.exists(local_path):
            return {
                'success': False,
                'error': f'Local path does not exist: {local_path}',
                'operation': operation
            }
        
        if direction == "download":
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
        
        process = await asyncio.create_subprocess_exec(
            *scp_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        stdout_text = stdout.decode('utf-8', errors='replace')
        stderr_text = stderr.decode('utf-8', errors='replace')
        
        return {
            'success': process.returncode == 0,
            'exit_code': process.returncode,
            'stdout': stdout_text,
            'stderr': stderr_text,
            'operation': operation,
            'local_path': local_path,
            'remote_path': remote_path,
            'direction': direction,
            'recursive': recursive
        }
        
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': f'Transfer timeout after {timeout} seconds',
            'operation': operation,
            'local_path': local_path,
            'remote_path': remote_path
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'operation': operation,
            'local_path': local_path,
            'remote_path': remote_path
        }    