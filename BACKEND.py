import os
import sys
import time
import threading
import mysql.connector
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# ======================== Clase Database ========================
class Database:
    def __init__(self):
        load_dotenv()  # Carga variables de entorno desde .env
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.database = os.getenv("DB_NAME", "")

    def get_connection(self):
        """Crea y retorna una conexión a MySQL."""
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return conn
        except mysql.connector.Error as err:
            print(f"Error al conectar a la base de datos: {err}")
            return None

# ======================== Clase AuthService ========================
class AuthService:

    def __init__(self, db: Database):
        self.db = db

    def delete_user_account(self, user_id: int) -> bool:
        """Elimina la cuenta del usuario junto con sus sesiones y mensajes."""
        conn = self.db.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            # Eliminar los mensajes asociados a las sesiones del usuario
            cursor.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id = %s)", (user_id,))
            # Eliminar las sesiones del usuario
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            # Eliminar la cuenta del usuario
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            print("Cuenta eliminada exitosamente.")
            return True
        except mysql.connector.Error as err:
            print(f"Error al eliminar la cuenta: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def register_user(self, username: str, password: str) -> bool:
        """Registra un nuevo usuario. Retorna True si se registró con éxito."""
        conn = self.db.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                print("El usuario ya existe.")
                return False
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
            print("Usuario registrado con éxito.")
            return True
        except mysql.connector.Error as err:
            print(f"Error en register_user: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def login_user(self, username: str, password: str) -> int:
        """Verifica usuario y contraseña. Retorna el 'id' del usuario si es correcto."""
        conn = self.db.get_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            if row:
                user_id, stored_password = row
                if stored_password == password:
                    print("¡Login exitoso!")
                    return user_id
            print("Usuario o contraseña incorrectos.")
            return 0
        except mysql.connector.Error as err:
            print(f"Error en login_user: {err}")
            return 0
        finally:
            cursor.close()
            conn.close()

# ======================== Clase ChatService ========================
class ChatService:

    def __init__(self, db: Database):
        self.db = db

    def delete_all_user_chats(self, user_id: int) -> bool:
        """Elimina todas las sesiones de chat y sus mensajes asociados para un usuario."""
        conn = self.db.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            # Eliminar los mensajes asociados a las sesiones del usuario
            cursor.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id = %s)", (user_id,))
            # Eliminar las sesiones del usuario
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            conn.commit()
            print("Todos los chats han sido eliminados exitosamente.")
            return True
        except mysql.connector.Error as err:
            print(f"Error al eliminar todos los chats: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def rename_chat_session(self, session_id: int, new_name: str) -> bool:
        """Renombra una sesión de chat dado su ID."""
        conn = self.db.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chat_sessions SET session_name = %s WHERE id = %s",
                (new_name, session_id)
            )
            conn.commit()
            print("Sesión renombrada exitosamente.")
            return True
        except mysql.connector.Error as err:
            print(f"Error al renombrar la sesión: {err}")
            return False
        finally:
            cursor.close()
            conn.close()
    def delete_chat_session(self, session_id: int) -> bool:
        """Elimina una sesión de chat y sus mensajes asociados."""
        conn = self.db.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            # Primero eliminar los mensajes asociados
            cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            # Luego eliminar la sesión
            cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
            conn.commit()
            print("Sesión eliminada exitosamente.")
            return True
        except mysql.connector.Error as err:
            print(f"Error al eliminar la sesión: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def create_chat_session(self, user_id: int, session_name: str = "Sesión de Chat") -> int:
        """Crea una nueva sesión de chat para el usuario y retorna su ID."""
        conn = self.db.get_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_sessions (user_id, session_name)
                VALUES (%s, %s)
                """,
                (user_id, session_name)
            )
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error al crear la sesión: {err}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def get_user_sessions(self, user_id: int) -> list:
        """Retorna una lista de (session_id, session_name) de las sesiones del usuario, ordenadas por fecha de creación descendente."""
        conn = self.db.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_name 
                FROM chat_sessions 
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error al obtener sesiones: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def save_message(self, session_id: int, role: str, message: str) -> None:
        """Guarda un mensaje en la tabla 'messages'."""
        conn = self.db.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (session_id, role, message) 
                VALUES (%s, %s, %s)
                """,
                (session_id, role, message)
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error al guardar el mensaje: {err}")
        finally:
            cursor.close()
            conn.close()

    def load_messages(self, session_id: int) -> list:
        """Retorna los mensajes de la sesión en forma de lista de tuplas (role, message)."""
        conn = self.db.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, message 
                FROM messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC
                """,
                (session_id,)
            )
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error al cargar mensajes: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

# ======================== Clase ChatModel ========================
class ChatModel:
    def __init__(self):
        self.api_token = os.getenv('HUGGINGFACEHUB_API_TOKEN')
        if not self.api_token:
            raise ValueError("El token de Hugging Face no está configurado. Agrega tu token en un archivo .env.")

        self.client = InferenceClient(
            model="meta-llama/Llama-2-7b-chat-hf",
            token=self.api_token
        )

    def generar_respuesta_dinamica(self, contexto, entrada_usuario):
        # Añadir instrucciones dinámicas al modelo basadas en la entrada del usuario
        if "triste" in entrada_usuario.lower() or "deprimido" in entrada_usuario.lower():
            contexto += " Por favor, ofrece consejos prácticos y reconfortantes para alguien que se siente triste. Ayuda al usuario a encontrar formas de sentirse mejor."
        elif "superar" in entrada_usuario.lower() or "ayuda" in entrada_usuario.lower():
            contexto += " Brinda pasos claros y consejos específicos sobre cómo superar una situación difícil o emocional."
        elif "solo" in entrada_usuario.lower():
            contexto += " Responde con empatía y sugiere formas de conectarse con los demás o mejorar el estado emocional."
        else:
            contexto += " Responde de forma empática y adaptada al contexto del usuario."
        contexto += " Responde exclusivamente en español, sin incluir texto en otros idiomas."
        return contexto

    def verificar_respuesta_completa(self, respuesta):
        # Validar si la respuesta está incompleta y solicitar continuación si es necesario
        if respuesta.endswith("...") or len(respuesta.split()) < 15:
            return True
        return False

    def generate_response(self, contexto_actualizado, contexto_dinamico):
        try:
            # Realiza la animación mientras espera la respuesta
            stop_event = threading.Event()
            hilo_animacion = threading.Thread(target=self.animacion_respuesta, args=(stop_event,))
            hilo_animacion.start()

            # Obtener la respuesta de la API
            respuesta = self.client.text_generation(contexto_actualizado + contexto_dinamico, max_new_tokens=400)

            # Validar si la respuesta está incompleta
            if self.verificar_respuesta_completa(respuesta):
                respuesta += self.client.text_generation("Continúa: " + respuesta, max_new_tokens=150)

            # Detener la animación y limpiar
            stop_event.set()
            hilo_animacion.join()
            sys.stdout.write("" + " " * 30 + "")

            # Filtrar la respuesta para eliminar posibles entradas generadas del usuario
            respuesta_filtrada = respuesta.split("Usuario:")[0].strip()
            return respuesta_filtrada
        except Exception as e:
            print(f"Error al consultar el modelo: {e}")
            return "Lo siento, hubo un error al procesar tu solicitud."

    def animacion_respuesta(self, stop_event):
        """Simula una animación de escritura mientras no se detenga."""
        animacion = "|/-\\"
        while not stop_event.is_set():
            for frame in animacion:
                if stop_event.is_set():
                    break
                sys.stdout.write(f"El chatbot está respondiendo {frame}")
                sys.stdout.flush()
                time.sleep(0.2)

    def generate_response(self, prompt: str, max_new_tokens: int = 300) -> str:
        try:
            response = self.client.text_generation(prompt, max_new_tokens=max_new_tokens)
            return response
        except Exception as e:
            print(f"Error al generar respuesta: {e}")
            return "Lo siento, hubo un error al procesar tu solicitud."

# ======================== Clase ChatApplication ========================
class ChatApplication:
    def __init__(self):
        self.db = Database()
        self.auth_service = AuthService(self.db)
        self.chat_service = ChatService(self.db)
        self.chat_model = ChatModel()

    def start(self):
        print("\n=== Bienvenido a la aplicación de chat ===\n")
        user_id = self._handle_auth_flow()
        if not user_id:
            print("No se pudo iniciar sesión. Saliendo del programa.")
            return

        session_id = self._select_or_create_chat_session(user_id)
        if not session_id:
            print("No se pudo crear/seleccionar la sesión. Saliendo del programa.")
            return

        print(f"\nSesión seleccionada con ID={session_id}\n")
        historial = self._build_historial(session_id)
        print("Historial de la sesión:")
        for mensaje in historial:
            print(mensaje)
        print("¡Listo! Escribe 'salir' para terminar la sesión.\n")

        while True:
            entrada_usuario = input("Tú: ").strip()
            if entrada_usuario.lower() == "salir":
                print("\nSesión finalizada. ¡Hasta pronto!\n")
                break

            self.chat_service.save_message(session_id, "USER", entrada_usuario)
            historial.append(f"Usuario: {entrada_usuario}")
            prompt = self._construct_prompt(historial)

            stop_event = threading.Event()
            hilo = threading.Thread(target=self._animacion_respuesta, args=(stop_event,))
            hilo.start()

            respuesta_completa = self.chat_model.generate_response(prompt)
            respuesta = respuesta_completa.split('Usuario:')[0].strip()

            stop_event.set()
            hilo.join()
            sys.stdout.write("\r" + " " * 60 + "\r")

            print(f"IA: {respuesta}\n")
            self.chat_service.save_message(session_id, "ASSISTANT", respuesta)
            historial.append(f"IA: {respuesta}")

    def _handle_auth_flow(self) -> int:
        while True:
            opcion = input("¿Deseas [1] Iniciar sesión, [2] Registrarte? (1/2): ").strip()
            if opcion == "1": 
                username = input("Nombre de usuario: ").strip()
                password = input("Contraseña: ").strip()
                user_id = self.auth_service.login_user(username, password)
                if user_id:
                    return user_id
            elif opcion == "2":
                username = input("Elige un nombre de usuario: ").strip()
                password = input("Elige una contraseña: ").strip()
                if self.auth_service.register_user(username, password):
                    user_id = self.auth_service.login_user(username, password)
                    if user_id:
                        return user_id
            else:
                print("Opción inválida. Intenta de nuevo.")
           
    def _select_or_create_chat_session(self, user_id: int) -> int:
        sesiones = self.chat_service.get_user_sessions(user_id)
        if sesiones:
            print("Sesiones existentes:")
            for idx, (sid, sname) in enumerate(sesiones, start=1):
                print(f"{idx}. {sname} (ID: {sid})")
            print(f"{len(sesiones)+1}. Crear nueva sesión")
            print(f"{len(sesiones)+2}. Renombrar una sesión")
            print(f"{len(sesiones)+3}. Eliminar una sesión")
            print(f"{len(sesiones)+4}. Eliminar mi cuenta")
            print(f"{len(sesiones)+5}. Eliminar todos los chats")

            seleccion = input("Elige una opción: ").strip()
            try:
                seleccion = int(seleccion)
                if 1 <= seleccion <= len(sesiones):
                    return sesiones[seleccion-1][0]
                elif seleccion == len(sesiones) + 1:
                    sname = input("Nombre para la nueva sesión: ").strip()
                    return self.chat_service.create_chat_session(user_id, sname or "Sesión Nueva")
                elif seleccion == len(sesiones) + 2:
                    self._rename_chat_session(user_id)
                    return 0
                elif seleccion == len(sesiones) + 3:
                    self._delete_chat_session(user_id)
                    return 0
                elif seleccion == len(sesiones) + 4:
                    self._delete_user_account(user_id)
                    return 0
                elif seleccion == len(sesiones) + 5:
                    self._delete_all_user_chats(user_id)
                    return 0
                else:
                    print("Opción inválida. Volviendo al menú principal.")
                    return 0
            except ValueError:
                print("Opción inválida. Volviendo al menú principal.")
                return 0
        else:
            print("No tienes sesiones. Creando la primera sesión automáticamente.")
            return self.chat_service.create_chat_session(user_id, "Sesión Inicial")

    def _delete_all_user_chats(self, user_id: int):
        confirmacion = input("Si estás seguro de eliminar todos tus chats escribe: ELIMINAR").strip()
        if confirmacion == "ELIMINAR":
            if self.chat_service.delete_all_user_chats(user_id):
                print("Todos tus chats han sido eliminados correctamente.")
            else:
                print("Hubo un problema al eliminar tus chats. Por favor, inténtalo nuevamente.")
        else:
            print("Eliminación de chats cancelada. Volviendo al menú principal.")
        sesiones = self.chat_service.get_user_sessions(user_id)
        if sesiones:
            print("Sesiones existentes:")
            for idx, (sid, sname) in enumerate(sesiones, start=1):
                print(f"{idx}. {sname} (ID: {sid})")
            print(f"{len(sesiones)+1}. Crear nueva sesión")
            print(f"{len(sesiones)+2}. Renombrar una sesión")
            print(f"{len(sesiones)+3}. Eliminar una sesión")
            print(f"{len(sesiones)+4}. Eliminar mi cuenta")

            seleccion = input("Elige una opción: ").strip()
            try:
                seleccion = int(seleccion)
                if 1 <= seleccion <= len(sesiones):
                    return sesiones[seleccion-1][0]
                elif seleccion == len(sesiones) + 1:
                    sname = input("Nombre para la nueva sesión: ").strip()
                    return self.chat_service.create_chat_session(user_id, sname or "Sesión Nueva")
                elif seleccion == len(sesiones) + 2:
                    self._rename_chat_session(user_id)
                    return 0
                elif seleccion == len(sesiones) + 3:
                    self._delete_chat_session(user_id)
                    return 0
                elif seleccion == len(sesiones) + 4:
                    self._delete_user_account(user_id)
                    return 0
                else:
                    print("Opción inválida. Volviendo al menú principal.")
                    return 0
            except ValueError:
                print("Opción inválida. Volviendo al menú principal.")
                return 0
        else:
            print("No tienes sesiones. Creando la primera sesión automáticamente.")
            return self.chat_service.create_chat_session(user_id, "Sesión Inicial")

    def _delete_user_account(self, user_id: int):
        confirmacion = input("Si estás seguro de eliminar tu cuenta escribe: ELIMINAR").strip()
        if confirmacion == "ELIMINAR":
            if self.auth_service.delete_user_account(user_id):
                print("Tu cuenta ha sido eliminada correctamente. Cerrando sesión...")
                sys.exit()  # Finaliza el programa tras eliminar la cuenta
            else:
                print("Hubo un problema al eliminar tu cuenta. Por favor, inténtalo nuevamente.")
        else:
            print("Eliminación cancelada. Volviendo al menú principal.")
        sesiones = self.chat_service.get_user_sessions(user_id)
        if sesiones:
            print("Sesiones existentes:")
            for idx, (sid, sname) in enumerate(sesiones, start=1):
                print(f"{idx}. {sname} (ID: {sid})")
            print(f"{len(sesiones)+1}. Crear nueva sesión")
            print(f"{len(sesiones)+2}. Renombrar una sesión")
            print(f"{len(sesiones)+3}. Eliminar una sesión")

            seleccion = input("Elige una opción: ").strip()
            try:
                seleccion = int(seleccion)
                if 1 <= seleccion <= len(sesiones):
                    return sesiones[seleccion-1][0]
                elif seleccion == len(sesiones) + 1:
                    sname = input("Nombre para la nueva sesión: ").strip()
                    return self.chat_service.create_chat_session(user_id, sname or "Sesión Nueva")
                elif seleccion == len(sesiones) + 2:
                    self._rename_chat_session(user_id)
                    return 0
                elif seleccion == len(sesiones) + 3:
                    self._delete_chat_session(user_id)
                    return 0
                else:
                    print("Opción inválida. Volviendo al menú principal.")
                    return 0
            except ValueError:
                print("Opción inválida. Volviendo al menú principal.")
                return 0
        else:
            print("No tienes sesiones. Creando la primera sesión automáticamente.")
            return self.chat_service.create_chat_session(user_id, "Sesión Inicial")

    def _rename_chat_session(self, user_id: int):
        sesiones = self.chat_service.get_user_sessions(user_id)
        if not sesiones:
            print("No hay sesiones para renombrar.")
            return

        print("Sesiones disponibles para renombrar:")
        for idx, (sid, sname) in enumerate(sesiones, start=1):
            print(f"{idx}. {sname} (ID: {sid})")

        seleccion = input("Elige una sesión para renombrar: ").strip()
        try:
            seleccion = int(seleccion)
            if 1 <= seleccion <= len(sesiones):
                session_id = sesiones[seleccion-1][0]
                new_name = input("Nuevo nombre para la sesión: ").strip()
                if self.chat_service.rename_chat_session(session_id, new_name):
                    print("Sesión renombrada correctamente.")
                else:
                    print("No se pudo renombrar la sesión.")
            else:
                print("Opción inválida.")
        except ValueError:
            print("Opción inválida.")
        sesiones = self.chat_service.get_user_sessions(user_id)
        if sesiones:
            print("Sesiones existentes:")
            for idx, (sid, sname) in enumerate(sesiones, start=1):
                print(f"{idx}. {sname} (ID: {sid})")
            print(f"{len(sesiones)+1}. Crear nueva sesión")
            print(f"{len(sesiones)+2}. Eliminar una sesión")

            seleccion = input("Elige una opción: ").strip()
            try:
                seleccion = int(seleccion)
                if 1 <= seleccion <= len(sesiones):
                    return sesiones[seleccion-1][0]
                elif seleccion == len(sesiones) + 1:
                    sname = input("Nombre para la nueva sesión: ").strip()
                    return self.chat_service.create_chat_session(user_id, sname or "Sesión Nueva")
                elif seleccion == len(sesiones) + 2:
                    self._delete_chat_session(user_id)
                    return 0
                else:
                    print("Opción inválida. Volviendo al menú principal.")
                    return 0
            except ValueError:
                print("Opción inválida. Volviendo al menú principal.")
                return 0
        else:
            print("No tienes sesiones. Creando la primera sesión automáticamente.")
            return self.chat_service.create_chat_session(user_id, "Sesión Inicial")

    def _delete_chat_session(self, user_id: int):
        sesiones = self.chat_service.get_user_sessions(user_id)
        if not sesiones:
            print("No hay sesiones para eliminar.")
            return

        print("Sesiones disponibles para eliminar:")
        for idx, (sid, sname) in enumerate(sesiones, start=1):
            print(f"{idx}. {sname} (ID: {sid})")

        seleccion = input("Elige una sesión para eliminar: ").strip()
        try:
            seleccion = int(seleccion)
            if 1 <= seleccion <= len(sesiones):
                session_id = sesiones[seleccion-1][0]
                if self.chat_service.delete_chat_session(session_id):
                    print("Sesión eliminada correctamente.")
                else:
                    print("No se pudo eliminar la sesión.")
            else:
                print("Opción inválida.")
        except ValueError:
            print("Opción inválida.")
        sesiones = self.chat_service.get_user_sessions(user_id)
        if sesiones:
            print("\nSesiones existentes:")
            for idx, (sid, sname) in enumerate(sesiones, start=1):
                print(f"{idx}. {sname} (ID: {sid})")
            print(f"{len(sesiones)+1}. Crear nueva sesión")

            seleccion = input("\nElige una opción: ").strip()
            try:
                seleccion = int(seleccion)
                if 1 <= seleccion <= len(sesiones):
                    return sesiones[seleccion-1][0]
                else:
                    sname = input("Nombre para la nueva sesión: ").strip()
                    return self.chat_service.create_chat_session(user_id, sname or "Sesión Nueva")
            except ValueError:
                print("Opción inválida. Creando nueva sesión por defecto.")
                return self.chat_service.create_chat_session(user_id, "Sesión Nueva")
        else:
            print("No tienes sesiones. Creando la primera sesión automáticamente.")
            return self.chat_service.create_chat_session(user_id, "Sesión Inicial")

    def _build_historial(self, session_id: int) -> list:
        mensajes = self.chat_service.load_messages(session_id)
        return [f"{'Usuario' if role == 'USER' else 'IA'}: {msg}" for role, msg in mensajes]

    def _construct_prompt(self, historial: list) -> str:
        """Construye el prompt para el modelo a partir del historial."""
        contexto_base = (
            "Eres un asistente amigable y versátil que responde de manera clara y precisa a todas las preguntas. "
            "Para preguntas relacionadas con apoyo psicológico, responde empáticamente y adaptándote a las necesidades emocionales del usuario. "
            "Para preguntas generales, proporciona información correcta y amigable. Habla exclusivamente en español. "
            "Responde con claridad, evitando fragmentos incompletos o repeticiones innecesarias."
        )
        prompt = contexto_base
        for mensaje in historial:
            if mensaje.startswith("Usuario:"):
                prompt += f"Usuario: {mensaje[8:].strip()}"
            elif mensaje.startswith("IA:"):
                prompt += f"IA: {mensaje[3:].strip()}"
        prompt += "IA: "  # El modelo continuará desde este punto
        return prompt

    def _animacion_respuesta(self, stop_event: threading.Event):
        animacion = "|/-\\"
        while not stop_event.is_set():
            for frame in animacion:
                if stop_event.is_set():
                    break
                sys.stdout.write(f"\rEl chatbot está respondiendo {frame}")
                sys.stdout.flush()
                time.sleep(0.2)

# ======================== Ejecutar la aplicación ========================
if __name__ == "__main__":
    app = ChatApplication()
    app.start()
