import subprocess
import json
import os
import re
import sys

class VideoEngine:
    @staticmethod
    def get_ffmpeg_path(cmd_name):
        """Retorna o caminho do ffmpeg/ffprobe, priorizando a pasta local ou pasta do .exe"""
        # No Railway/Linux, simplesmente usamos o comando global 'ffmpeg' ou 'ffprobe'
        # que será instalado via Dockerfile.
        if os.name != 'nt':
            return cmd_name

        if getattr(sys, 'frozen', False):
            # Se for EXE, o FFmpeg está na mesma pasta do EXE ou no MEIPASS
            local_path = os.path.join(os.path.dirname(sys.executable), f"{cmd_name}.exe")
            if not os.path.exists(local_path):
                local_path = os.path.join(sys._MEIPASS, f"{cmd_name}.exe")
        else:
            base_path = os.path.dirname(__file__)
            local_path = os.path.join(base_path, f"{cmd_name}.exe")
        
        if os.path.exists(local_path):
            return local_path
        return cmd_name

    @staticmethod
    def get_video_info(file_path):
        try:
            ffprobe_path = VideoEngine.get_ffmpeg_path('ffprobe')
            
            # Configuração para esconder o terminal no Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE

            cmd = [
                ffprobe_path, 
                '-v', 'quiet', 
                '-print_format', 'json', 
                '-show_streams', 
                '-show_format', 
                file_path
            ]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                startupinfo=startupinfo
            )
            data = json.loads(result.stdout)
            
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                return None
            
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'codec': video_stream['codec_name'],
                'duration': float(data['format']['duration']),
                'format': data['format']['format_name']
            }
        except Exception as e:
            print(f"Erro ao ler info do vídeo: {e}")
            return None

    @staticmethod
    def time_to_seconds(time_str):
        try:
            h, m, s = time_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        except:
            return 0

    @staticmethod
    def merge_videos(intro_path, body_path, output_path, progress_callback=None):
        info_intro = VideoEngine.get_video_info(intro_path)
        info_body = VideoEngine.get_video_info(body_path)
        
        if not info_intro or not info_body:
            return False, "Não foi possível ler as informações dos vídeos."

        total_duration = info_intro['duration'] + info_body['duration']
        target_w = info_body['width']
        target_h = info_body['height']
        
        filter_complex = (
            f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},setsar=1[v0];"
            f"[1:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},setsar=1[v1];"
            f"[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[outv][outa]"
        )

        ffmpeg_path = VideoEngine.get_ffmpeg_path('ffmpeg')
        cmd = [
            ffmpeg_path, '-y',
            '-i', intro_path,
            '-i', body_path,
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '[outa]',
            '-c:v', 'libx264',
            '-preset', 'superfast',
            '-crf', '20',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-threads', '0',
            output_path
        ]

        try:
            # Configuração para esconder o terminal no Windows (IMPORTANTE)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE

            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True, 
                encoding='utf-8', 
                errors='replace',
                startupinfo=startupinfo
            )

            time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}.\d{2})")

            for line in process.stdout:
                match = time_regex.search(line)
                if match and progress_callback:
                    current_time = VideoEngine.time_to_seconds(match.group(1))
                    percentage = min(100, int((current_time / total_duration) * 100))
                    progress_callback(percentage, line.strip())
            
            process.wait()
            return process.returncode == 0, "Sucesso" if process.returncode == 0 else "Erro no processamento"
        except Exception as e:
            return False, str(e)
