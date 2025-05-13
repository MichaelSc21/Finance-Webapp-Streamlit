import streamlit as st


def show_state_main():
    for key, value in st.session_state.items():
        st.write(f"{key}: {value}")


if __name__ == '__main__':
    show_state_main()