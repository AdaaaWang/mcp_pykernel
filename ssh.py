import asyncio
import os
import mcp
from mcp.server import Server
from mcp.server.stdio import stdio_server

# 创建MCP server实例
app = Server("ssh-remote-executor")

# 全局配置变量
ssh_config = {
    'host': None,
    'username': None, 
    'key_path': None
}

async def run_ssh_command(command: str, timeout: int = 30) -> dict:
    """
    Run a command on the remote server via SSH.
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
        command
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


@mcp.tool()
async def ssh_connect(
    host: str,
    username: str, 
    key_path: str = "~/.ssh/nersc"
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
    # 验证SSH密钥文件是否存在
    key_full_path = os.path.expanduser(key_path)
    if not os.path.exists(key_full_path):
        return f"Error: SSH private key {key_full_path} does not exist. Please check the path."
    
    # 保存SSH配置
    ssh_config.update({
        'host': host,
        'username': username,
        'key_path': key_path
    })
    
    return f"SSH configuration: {username}@{host} (key: {key_path})"


@mcp.tool()
async def ssh_execute(
    command: str,
    timeout: int = 30
) -> str:
    """
    Excecute a command on the remote server via SSH.
    
    Args:
        command: bash command to execute on the remote server, in a string.
        timeout: timeout (seconds), default is 30 seconds
    
    Returns:
        Command execution result
    """
    result = await run_ssh_command(command, timeout)
    
    if result['success']:
        output = f"Excecution success!\n"
        output += f"Command: {result['command']}\n"
        output += f"Exit code: {result['exit_code']}\n"
        output += f"\n standard output:\n{result['stdout']}"
        if result['stderr']:
            output += f"\n Error:\n{result['stderr']}"
    else:
        output = f"Excecution failed!\n"
        output += f"Command: {result.get('command', command)}\n"
        output += f"Error: {result['error']}"
    
    return output


@mcp.tool()
async def run_python_script(
    script_name: str = "tst.py",
    working_directory: str = "",
    timeout: int = 60
) -> str:
    """
    Run a Python script on the remote server.
    
    Args:
        script_name: Name of the Python script to run (default tst.py)
        working_directory: Working directory to run the script in (default current directory)
        timeout: Timeout for the script execution (default 60 seconds)
    
    Returns:
        Execution result of the Python script, in a string.
    """
    if working_directory:
        command = f"cd {working_directory} && python {script_name}"
    else:
        command = f"python {script_name}"
    
    result = await run_ssh_command(command, timeout)
    
    if result['success']:
        output = f"Python script excecution done!\n"
        output += f"Script: {script_name}\n"
        if working_directory:
            output += f"Working directory: {working_directory}\n"
        output += f"Exit code: {result['exit_code']}\n"
        output += f"\n Output::\n{result['stdout']}"
        if result['stderr']:
            output += f"\n Error:\n{result['stderr']}"
    else:
        output = f"Python script excecution failed!\n"
        output += f"Script: {script_name}\n"
        output += f"Error: {result['error']}"
    
    return output


@mcp.tool()
async def check_remote_status() -> str:
    """
    Check the status of the remote server.
    This function runs several basic commands to gather server information.
    
    Returns:
        A summary of the remote server status, including current directory, file list, Python version, and uptime.
    """
    commands = [
        "pwd",           
        "ls -la",        
        "python --version",
        "uptime"         
    ]
    
    results = []
    for cmd in commands:
        result = await run_ssh_command(cmd, 10)
        if result['success']:
            results.append(f"Successful run {cmd}:\n{result['stdout'].strip()}\n")
        else:
            results.append(f"Error {cmd}: {result['error']}\n")
    
    return "Remote server status check:\n\n" + "\n".join(results)


async def main():
    """
    Main entry point for the MCP server.
    This function sets up the server and starts listening for requests.
    """
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
        

if __name__ == "__main__":
    asyncio.run(main())