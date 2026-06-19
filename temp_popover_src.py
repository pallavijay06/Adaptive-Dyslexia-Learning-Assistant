    @gather_metrics("popover")
    def popover(
        self,
        label: str,
        *,
        type: Literal["primary", "secondary", "tertiary"] = "secondary",
        help: str | None = None,
        icon: str | None = None,
        disabled: bool = False,
        use_container_width: bool | None = None,
        width: Width = "content",
        key: Key | None = None,
        on_change: Literal["ignore", "rerun"] | WidgetCallback = "ignore",
        args: WidgetArgs | None = None,
        kwargs: WidgetKwargs | None = None,
    ) -> PopoverContainer:
        r"""Insert a popover container.

        Inserts a multi-element container as a popover. It consists of a button-like
        element and a container that opens when the button is clicked.

        To add elements to the returned container, you can use the "with"
        notation (preferred) or just call methods directly on the returned object.
        See examples below.

        Interacting with widgets inside of an open popover will rerun the app
        while keeping the popover open. Clicking outside of the popover will
        close it.

        By default, all content within the popover is computed and sent to the
        frontend, and the app doesn't rerun when the popover is opened or
        closed. To enable lazy execution where content only runs when the
        popover is open, use ``on_change="rerun"`` or pass a callable to
        ``on_change``. The ``.open`` property indicates whether the popover is
        currently open, letting you conditionally render expensive content.

        .. note::
            To follow best design practices, don't nest popovers.

        Parameters
        ----------
        label : str
            The label of the button that opens the popover container.
            The label can optionally contain GitHub-flavored Markdown of the
            following types: Bold, Italics, Strikethroughs, Inline Code, Links,
            and Images. Images display like icons, with a max height equal to
            the font height.

            Unsupported Markdown elements are unwrapped so only their children
            (text contents) render. Common block-level Markdown (headings,
            lists, blockquotes) is automatically escaped and displays as
            literal text in labels.

            See the ``body`` parameter of |st.markdown|_ for additional,
            supported Markdown directives.

            .. |st.markdown| replace:: ``st.markdown``
            .. _st.markdown: https://docs.streamlit.io/develop/api-reference/text/st.markdown

        help : str or None
            A tooltip that gets displayed when the popover button is hovered
            over. If this is ``None`` (default), no tooltip is displayed.

            The tooltip can optionally contain GitHub-flavored Markdown,
            including the Markdown directives described in the ``body``
            parameter of ``st.markdown``.

        type : "primary", "secondary", or "tertiary"
            An optional string that specifies the button type. This can be one
            of the following:

            - ``"primary"``: The button's background is the app's primary color
              for additional emphasis.
            - ``"secondary"`` (default): The button's background coordinates
              with the app's background color for normal emphasis.
            - ``"tertiary"``: The button is plain text without a border or
              background for subtlety.

        icon : str
            An optional emoji or icon to display next to the button label. If ``icon``
            is ``None`` (default), no icon is displayed. If ``icon`` is a
            string, the following options are valid:

            - A single-character emoji. For example, you can set ``icon="🚨"``
              or ``icon="🔥"``. Emoji short codes are not supported.

            - An icon from the Material Symbols library (rounded style) in the
              format ``":material/icon_name:"`` where "icon_name" is the name
              of the icon in snake case.

              For example, ``icon=":material/thumb_up:"`` will display the
              Thumb Up icon. Find additional icons in the `Material Symbols \
              <https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Rounded>`_
              font library.

            - ``"spinner"``: Displays a spinner as an icon.

        disabled : bool
            An optional boolean that disables the popover button if set to
            ``True``. The default is ``False``.

        use_container_width : bool
            Whether to expand the button's width to fill its parent container.
            If ``use_container_width`` is ``False`` (default), Streamlit sizes
            the button to fit its content. If ``use_container_width`` is
            ``True``, the width of the button matches its parent container.

            In both cases, if the content of the button is wider than the
            parent container, the content will line wrap.

            The popover container's minimum width matches the width of its
            button. The popover container may be wider than its button to fit
            the container's content.

            .. deprecated::
                ``use_container_width`` is deprecated and will be removed in a
                future release. For ``use_container_width=True``, use
                ``width="stretch"``. For ``use_container_width=False``, use
                ``width="content"``.

        width : int, "stretch", or "content"
            The width of the button. This can be one of the following:

            - ``"content"`` (default): The width of the button matches the
              width of its content, but doesn't exceed the width of the parent
              container.
            - ``"stretch"``: The width of the button matches the width of the
              parent container.
            - An integer specifying the width in pixels: The button has a
              fixed width. If the specified width is greater than the width of
              the parent container, the width of the button matches the width
              of the parent container.

            The popover container's minimum width matches the width of its
            button. The popover container may be wider than its button to fit
            the container's contents.

        key : str, int, or None
            An optional string or integer to use as the unique key for
            the widget. If this is ``None`` (default), a key will be
            generated for the widget based on the values of the other
            parameters. No two widgets may have the same key.

            When ``on_change`` is set to ``"rerun"`` or a callable, setting a
            key lets you read or update the open/closed state via
            ``st.session_state[key]``. For more details, see `Widget behavior
            <https://docs.streamlit.io/develop/concepts/architecture/widget-behavior>`_.

            Additionally, if ``key`` is provided, it will be used as a
            CSS class name prefixed with ``st-key-``.

        on_change : "ignore", "rerun", or callable
            How the popover should respond when the user opens or closes it.
            This controls whether the popover tracks state and triggers
            reruns. ``on_change`` can be one of the following values:

            - ``"ignore"`` (default): The popover doesn't track state. All
              popover content runs regardless of whether the popover is open or
              closed. The ``.open`` attribute of the popover container returns
              ``None``.

            - ``"rerun"``: The popover tracks state. Streamlit reruns the app
              when the user opens or closes the popover. The ``.open``
              attribute of the popover container returns the current state,
              which is ``True`` if the popover is open and ``False`` if it's
              closed. This lets you skip expensive work when the popover is
              closed.

            - A callable: The popover tracks state. Streamlit executes the
              callable as a callback function and reruns the app when the user
              opens or closes the popover. The ``.open`` attribute of the
              popover container returns its state like when
              ``on_change="rerun"``. If you need to access the current state
              inside your callback, fetch it through Session State.

            When the popover tracks state, it can't be used inside Streamlit
            cache-decorated functions.

        args : list or tuple or None
            An optional list or tuple of args to pass to the ``on_change``
            callback.

        kwargs : dict or None
            An optional dict of kwargs to pass to the ``on_change`` callback.

        Returns
        -------
        PopoverContainer
            A ``PopoverContainer`` object with an ``.open`` property to return
            the current state of the popover if the popover tracks state.

        Examples
        --------
        **Example 1: Use context management**
        You can use the ``with`` notation to insert any element into a popover:

        .. code-block:: python
            :filename: streamlit_app.py

            import streamlit as st

            with st.popover("Open popover"):
                st.markdown("Hello World 👋")
                name = st.text_input("What's your name?")

            st.write("Your name:", name)

        .. output::
            https://doc-popover.streamlit.app/
            height: 400px

        **Example 2: Call methods directly**

        You can call methods directly on the returned object:

        .. code-block:: python
            :filename: streamlit_app.py

            import streamlit as st

            popover = st.popover("Filter items")
            red = popover.checkbox("Show red items.", True)
            blue = popover.checkbox("Show blue items.", True)

            if red:
                st.write(":red[This is a red item.]")
            if blue:
                st.write(":blue[This is a blue item.]")

        .. output::
            https://doc-popover2.streamlit.app/
            height: 400px

        **Example 3: Programmatically control the popover state**

        You can use a key to programmatically control the popover state or
        access the state in callbacks. You must set the ``on_change`` parameter
        for the popover to track state.

        .. code-block:: python
            :filename: streamlit_app.py

            import streamlit as st


            def toggle_popover():
                st.session_state.drawer = not st.session_state.drawer

            def on_popover_change():
                if st.session_state.drawer:
                    st.toast("You opened the popover.")
                else:
                    st.toast("You closed the popover.")


            with st.popover("Open popover", on_change=on_popover_change, key="drawer"):
                st.write("This is the popover")
                st.button("Close popover", on_click=toggle_popover)

            st.button("Open popover", on_click=toggle_popover)

        .. output::
            https://doc-popover-callback.streamlit.app/
            height: 300px

        """
        if label is None:
            raise StreamlitAPIException("A label is required for a popover")

        if use_container_width is not None:
            width = "stretch" if use_container_width else "content"

        # Checks whether the entered button type is one of the allowed options
        if type not in {"primary", "secondary", "tertiary"}:
            raise StreamlitAPIException(
                'The type argument to st.popover must be "primary", "secondary", or "tertiary". '
                f'\nThe argument passed was "{type}".'
            )

        if not callable(on_change) and on_change not in {"ignore", "rerun"}:
            raise StreamlitValueError(
                "on_change", ["'rerun'", "'ignore'", "a callback function"]
            )

        key = to_key(key)
        is_stateful = on_change != "ignore"

        current_open = False
        element_id: str | None = None
        block_id: str | None = None

        if is_stateful:
            is_callback = callable(on_change)
            check_widget_policies(
                self.dg,
                key,
                on_change=cast("WidgetCallback", on_change) if is_callback else None,
                default_value=None,
                writes_allowed=True,
                enable_check_callback_rules=is_callback,
            )

            ctx = get_script_run_ctx()

            element_id = compute_and_register_element_id(
                "popover",
                user_key=key,
                key_as_main_identity=False,
                dg=self.dg,
                label=label,
                type=type,
                help=help,
                icon=icon,
                disabled=disabled,
                width=width,
            )
            block_id = element_id

            serde = _PopoverSerde()

            popover_state = register_widget(
                element_id,
                deserializer=serde.deserialize,
                serializer=serde.serialize,
                ctx=ctx,
                value_type="bool_value",
                on_change_handler=on_change if callable(on_change) else None,
                args=args if callable(on_change) else None,
                kwargs=kwargs if callable(on_change) else None,
            )

            current_open = popover_state.value
        elif key is not None:
            block_id = compute_and_register_element_id(
                "popover",
                user_key=key,
                key_as_main_identity=False,
                dg=self.dg,
            )

        popover_proto = BlockProto.Popover()
        popover_proto.label = label
        popover_proto.disabled = disabled
        popover_proto.type = type
        popover_proto.open = current_open
        if help:
            popover_proto.help = str(help)
        if icon is not None:
            popover_proto.icon = validate_icon_or_emoji(icon)

        if is_stateful and element_id is not None:
            popover_proto.id = element_id

        block_proto = BlockProto()
        block_proto.allow_empty = True
        block_proto.popover.CopyFrom(popover_proto)

        validate_width(width, allow_content=True)
        block_proto.width_config.CopyFrom(get_width_config(width))

        if block_id is not None:
            block_proto.id = block_id

        popover_dg = cast(
            "PopoverContainer",
            self.dg._block(
                block_proto=block_proto,
                dg_type=get_dg_singleton_instance().popover_container_cls,
            ),
        )

        if is_stateful:
            popover_dg.open = current_open

        return popover_dg
