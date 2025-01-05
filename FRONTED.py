import flet as ft
import threading
import time
import sys


class ChatApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Chatbot con Flet"
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        self.page.vertical_alignment = ft.MainAxisAlignment.START

        # Lista para mantener el orden de creación de los chats
        self.chat_order = []  # Mantiene el orden de los chats
        self.chats = {}  # {chat_id: [(mensaje, is_user)]}
        self.active_chat = None  # Chat actualmente seleccionado
        self.chat_counter = 0  # Contador para generar identificadores únicos

        # Para manejar threads de respuestas del bot
        self.bot_thread = None
        self.cancel_bot_response = threading.Event()

        # Componentes dinámicos
        self.chat_list = ft.Column(scroll="auto", expand=True)  # Lista de chats
        self.messages_container = ft.Column(scroll="auto", expand=True)  # Mensajes
        self.typing_indicator = ft.Text(
            "El bot está escribiendo...", visible=False, size=14, italic=True
        )
        self.options_button = ft.IconButton(  # Inicializar el botón de opciones
            icon=ft.Icons.MORE_VERT,
            on_click=self.show_chat_options,
            tooltip="Opciones del chat",
            visible=False,
        )
        #self.chat_title = ft.Text("Chatbot", size=20, weight="bold")  # Título dinámico del chat
        #ft.Text("Bienvenido a MINDCARE mateo", size=24, color=ft.Colors.GREY),
        self.chat_title = ft.Text("Chat", size=18, color=ft.Colors.GREY)  # Título dinámico del chat
    
        # Entrada de mensajes
        self.user_input = ft.TextField(
            hint_text="Escribe tu mensaje...",
            expand=True,
            disabled=True,
            on_submit=self.send_message,
        )
        self.send_button = ft.ElevatedButton(
            "Enviar", on_click=self.send_message, disabled=True
        )

    def build_ui(self):
        """
        Construye la interfaz gráfica principal.
        """
        self.page.add(
            ft.Row(
                controls=[
                    # Panel izquierdo: lista de chats y configuración
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    controls=[
                                        ft.Text("Chats", size=18, weight="bold"),
                                        ft.IconButton(
                                            icon=ft.Icons.ADD,
                                            on_click=self.add_chat,
                                            tooltip="Agregar chat",
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                self.chat_list,
                                ft.Divider(),
                                ft.IconButton(
                                    icon=ft.Icons.SETTINGS,
                                    on_click=self.show_settings_menu,
                                    tooltip="Configuración",
                                ),
                            ],
                            expand=True,
                        ),
                        width=200,
                        padding=10,
                        bgcolor="#EEEEEE",
                    ),
                    # Panel derecho: área de mensajes
                    ft.Column(
                        controls=[
                            ft.Text("Bienvenido a MINDCARE mateo", size=18, weight="bold"),
                            ft.Row(
                                controls=[
                                    self.chat_title,
                                    self.options_button,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(),
                            ft.Container(
                                content=self.messages_container, expand=True
                            ),
                            self.typing_indicator,
                            ft.Row(
                                [self.user_input, self.send_button],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        expand=True,
                    ),
                ],
                expand=True,
            )
        )
        self.show_welcome_message()

    # -------------------------------------------------------------------------
    # Configuración
    # -------------------------------------------------------------------------
    def show_settings_menu(self, e):
        """
        Muestra las opciones del menú de configuración.
        """
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Configuración"),
            content=ft.Column(
                controls=[
                    ft.TextButton(
                        text="Cerrar sesión",
                        on_click=self.confirm_logout,
                    ),
                    ft.TextButton(
                        text="Eliminar cuenta",
                        on_click=self.confirm_delete_account,
                    ),
                    ft.TextButton(
                        text="Eliminar todos los chats",
                        on_click=self.confirm_delete_all_chats,
                    ),
                    ft.TextButton(
                        text="Info.",
                        on_click=self.show_info,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def confirm_logout(self, e):
        """
        Muestra una ventana de confirmación para cerrar sesión.
        """
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cerrar sesión"),
            content=ft.Text("¿Estás seguro de que deseas cerrar sesión?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.TextButton("Cerrar sesión", on_click=lambda e: self.exit_app()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def confirm_delete_account(self, e):
        """
        Muestra una ventana para confirmar la eliminación de la cuenta.
        """
        input_field = ft.TextField(label="Escribe 'ELIMINAR' para confirmar")

        def on_confirm(e):
            if input_field.value.strip().upper() == "ELIMINAR":
                self.exit_app()
            else:
                input_field.error_text = "Palabra incorrecta, intenta nuevamente."
                input_field.update()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar cuenta"),
            content=input_field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.TextButton("Eliminar cuenta", on_click=on_confirm),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def confirm_delete_all_chats(self, e):
        """
        Muestra una ventana para confirmar la eliminación de todos los chats.
        """
        input_field = ft.TextField(label="Escribe 'ELIMINAR' para confirmar")

        def on_confirm(e):
            if input_field.value.strip().upper() == "ELIMINAR":
                self.chat_counter = 0 #Reiniciar el contador de chats
                self.chat_title.value = "Chat"
                self.options_button.visible = False  
                self.chat_order.clear()
                self.chats.clear()
                self.active_chat = None
                self.update_chat_list()
                self.load_messages()
                self.close_dialog()
            else:
                input_field.error_text = "Palabra incorrecta, intenta nuevamente."
                input_field.update()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar todos los chats"),
            content=input_field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.TextButton("Eliminar todos los chats", on_click=on_confirm),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def show_info(self, e):
        """
        Muestra información del programa.
        """
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Info"),
            content=ft.ListView(
                #controls=[ft.Text(f"Creadro: dfnsdifhdifuhsfiushfdsufhsufhdsuyfsdfuysgfdsufygsefuysgfuydgfsugdsdsfuygfsdgudfuygdsfuysdgsdfsfs")],
                controls=[ft.Text(f"Creadro: dfnsdifhdifuhsfiushfdsufhsufhdsuyfsdfuysgfdsufygseffhfhfhfghfhgfhghgfhghghfghfhfghfghfghfhfghfghfghfghfuysgfuydgfsugdsdsfuygfsdgudfuygdsfuysdgsdfsfs", size=16), 
                          ft.Text(f"Mateo ramos", size=16),
                          ft.Text(f"Mateo ramos", size=16),
                          ft.Text(f"Mateo ramos", size=16),
                          ft.Text(f"Mateo ramos", size=16)],
                height=100,  # Altura fija que permite el scroll si es necesario
                width=300,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()
    
    def exit_app(self):
        """
        Cierra el programa.
        """
        self.page.window_close()  # Cierra la ventana de la aplicación
        sys.exit(0)

    def close_dialog(self):
        """
        Cierra cualquier cuadro de diálogo activo.
        """
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

    def show_chat_options(self, e):
        """
        Muestra el menú emergente con opciones del chat activo.
        """
        if not self.active_chat:
            return

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Opciones del chat"),
            content=ft.Column(
                controls=[
                    ft.TextButton(
                        text="Ver nombre completo",
                        on_click=lambda e: self.show_full_name_dialog(self.active_chat),
                    ),
                    ft.TextButton(
                        text="Renombrar",
                        on_click=lambda e: self.rename_chat_dialog(self.active_chat),
                    ),
                    ft.TextButton(
                        text="Eliminar",
                        on_click=lambda e: self.delete_chat_dialog(self.active_chat),
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    # -------------------------------------------------------------------------
    # Manejo de Chats
    # -------------------------------------------------------------------------

    def add_chat(self, e):
        """
        Crea un nuevo chat y lo establece como activo.
        """
        self.chat_counter += 1
        chat_id = f"Chat {self.chat_counter}"
        self.chats[chat_id] = []  # Inicializa la lista de mensajes del chat
        self.chat_order.insert(0, chat_id)  # Agregar al inicio de la lista de orden
        self.switch_chat(chat_id)  # Cambia automáticamente al nuevo chat
        self.update_chat_list()

    def switch_chat(self, chat_id):
        """
        Cambia el chat activo.
        """
        if chat_id == self.active_chat:
            return  # Si ya está en el chat seleccionado, no hacer nada

        # Cancelar la respuesta del bot si está en proceso
        if self.bot_thread and self.bot_thread.is_alive():
            self.cancel_bot_response.set()
            self.bot_thread.join()  # Esperar a que termine el thread

        # Limpiar la bandera para futuras respuestas
        self.cancel_bot_response.clear()

        # Cambiar de chat
        self.active_chat = chat_id
        self.chat_title.value = chat_id if len(chat_id) <= 15 else f"{chat_id[:12]}..." # Actualizar el título del chat con truncamiento.
        self.options_button.visible = True  # Mostrar el botón de opciones del chat
        self.update_chat_list()
        self.load_messages()

    def update_chat_list(self):
        """
        Actualiza la lista de chats en el panel izquierdo.
        """
        self.chat_list.controls.clear()
        for chat_id in self.chat_order:
            is_active = chat_id == self.active_chat

            # Truncar nombres largos con puntos suspensivos
            truncated_name = chat_id if len(chat_id) <= 15 else f"{chat_id[:12]}..."
            
            # Botón del chat
            self.chat_list.controls.append(
                ft.TextButton(
                    text=truncated_name,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE if is_active else ft.Colors.TRANSPARENT,
                        color=ft.Colors.WHITE if is_active else ft.Colors.BLACK,
                    ),
                    on_click=lambda e, cid=chat_id: self.switch_chat(cid),
                )
            )
            
        self.page.update()

    def show_full_name_dialog(self, chat_id):
        """
        Muestra un cuadro de diálogo con el nombre completo del chat.
        """
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nombre completo."),
            content=ft.ListView(
                controls=[ft.Text(f"Nombre completo del chat:", size=16), 
                          ft.Text(f"{chat_id}", size=16)],
                height=100,  # Altura fija que permite el scroll si es necesario
                width=300,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def rename_chat_dialog(self, chat_id):
        """
        Muestra un cuadro de diálogo para renombrar el chat seleccionado.
        """
        rename_input = ft.TextField(label="Nuevo nombre", expand=True)

        def on_rename(e):
            new_name = rename_input.value.strip()
            if new_name and chat_id in self.chats:
                self.rename_chat(chat_id, new_name)
            self.close_dialog()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Renombrar chat"),
            content=rename_input,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.TextButton("Renombrar", on_click=on_rename),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def delete_chat_dialog(self, chat_id):
        """
        Muestra un cuadro de diálogo para eliminar un chat seleccionado.
        """
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar chat"),
            content=ft.Text(f"¿Estás seguro de que deseas eliminar '{chat_id}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.TextButton(
                    "Eliminar",
                    on_click=lambda e, cid=chat_id: self.confirm_delete_chat(cid),
                ),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def confirm_delete_chat(self, chat_id):
        """
        Confirma la eliminación del chat y cierra el cuadro de diálogo.
        """
        if chat_id in self.chats:
            del self.chats[chat_id]
            self.chat_order.remove(chat_id)
        if chat_id == self.active_chat:
            self.active_chat = next(iter(self.chat_order), None)
            self.chat_title.value = self.chat_order[0]  # Actualizar el título del chat

        self.update_chat_list()
        self.load_messages()
        self.close_dialog()

    def rename_chat(self, old_name, new_name):
        """
        Renombra un chat existente.
        """
        self.chats[new_name] = self.chats.pop(old_name)
        index = self.chat_order.index(old_name)
        self.chat_order[index] = new_name  # Mantener el orden al renombrar
        if self.active_chat == old_name:
            self.active_chat = new_name
            self.chat_title.value = new_name if len(new_name) <= 15 else f"{new_name[:12]}..."  # Actualizar el título del chat renombrado con truncamiento.
        self.update_chat_list()
        self.load_messages()

    def load_messages(self):
        """
        Carga los mensajes del chat activo y los muestra en la UI.
        """
        self.messages_container.controls.clear()

        if self.active_chat is None or self.active_chat not in self.chats:
            self.show_welcome_message()
            return

        # Cargar mensajes del chat activo
        for msg, is_user in self.chats[self.active_chat]:
            alignment = (
                ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
            )
            color = "#2196F3" if is_user else "#4CAF50"
            self.messages_container.controls.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(msg, color="white", size=16),
                            bgcolor=color,
                            padding=10,
                            margin=5,
                            border_radius=5,
                        )
                    ],
                    alignment=alignment,
                )
            )

        # Habilitar entrada de texto
        self.user_input.disabled = False
        self.send_button.disabled = False
        self.page.update()

    def show_welcome_message(self):
        """
        Muestra el mensaje de bienvenida si no hay chats activos.
        """
        self.messages_container.controls.clear()
        self.messages_container.controls.append(
            ft.Container(
                content=ft.Text(
                    "MINDCARE\nBienvenido, haz clic en el botón + para comenzar.",
                    size=16,
                    color=ft.Colors.BLACK54,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        self.user_input.disabled = True
        self.send_button.disabled = True
        self.page.update()

    def send_message(self, e):
        """
        Envía un mensaje desde el usuario.
        """
        if not self.active_chat:
            return

        user_text = self.user_input.value.strip()
        if not user_text:
            return

        self.add_message(user_text, is_user=True)
        self.user_input.value = ""
        self.page.update()

        # Simular respuesta del bot
        self.bot_thread = threading.Thread(
            target=self.simulate_bot_response, args=(user_text,)
        )
        self.bot_thread.start()

    def simulate_bot_response(self, user_message):
        """
        Simula una respuesta del bot con un retraso.
        """
        self.typing_indicator.visible = True
        self.page.update()

        for _ in range(20):  # Simula un proceso largo con 2 segundos en total
            if self.cancel_bot_response.is_set():
                self.typing_indicator.visible = False
                self.page.update()
                return
            time.sleep(0.1)

        self.typing_indicator.visible = False
        self.add_message(f"Bot: Respuesta a '{user_message}'", is_user=False)
        self.page.update()

    def add_message(self, text, is_user=True):
        """
        Agrega un mensaje a la conversación del chat activo.
        """
        alignment = (
            ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
        )
        color = "#2196F3" if is_user else "#4CAF50"

        # Agregar el mensaje a la columna
        self.messages_container.controls.append(
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text(text, color="white", size=16),
                        bgcolor=color,
                        padding=10,
                        margin=5,
                        border_radius=5,
                    )
                ],
                alignment=alignment,
            )
        )

        # Guardar el mensaje en el estado del chat activo
        if self.active_chat:
            self.chats[self.active_chat].append((text, is_user))


def main(page: ft.Page):
    app = ChatApp(page)
    app.build_ui()


if __name__ == "__main__":
    ft.app(target=main)
