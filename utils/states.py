from aiogram.fsm.state import State, StatesGroup

class SearchStates(StatesGroup):
    waiting_for_query = State()

class UploadBookStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_subject = State()
    waiting_for_file = State()
    waiting_for_description = State()
    confirm_upload = State()

class UploadScheduleStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_file = State()
    waiting_for_description = State()
    confirm_upload = State()

class SuggestSubjectStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_name = State()
    waiting_for_doctor = State()
    confirm_suggestion = State()

class AddLectureStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_subject = State()
    waiting_for_spec = State()
    waiting_for_lecture_name = State()
    confirm_add = State()

class UploadVideoStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_subject = State()
    waiting_for_spec = State()
    waiting_for_lecture = State()
    waiting_for_title = State()
    waiting_for_video_content = State() # video file or external url
    waiting_for_description = State()
    confirm_upload = State()

class UploadFileStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_subject = State()
    waiting_for_spec = State()
    waiting_for_lecture = State()
    waiting_for_category = State()
    waiting_for_file_name = State()
    waiting_for_file_document = State()
    waiting_for_description = State()
    confirm_upload = State()
    # Consecutive upload states
    waiting_for_next_file_name = State()
    waiting_for_next_file_document = State()
    waiting_for_next_description = State()
    confirm_next_upload = State()

class AdminStates(StatesGroup):
    waiting_for_new_link_title = State()
    waiting_for_new_link_url = State()
    waiting_for_edit_link_title = State()
    waiting_for_edit_link_url = State()
    waiting_for_edit_subject_name = State()
    waiting_for_edit_subject_doctor = State()
    waiting_for_edit_spec_name = State()
    waiting_for_new_spec_name = State()
    waiting_for_ban_user_id = State()
    waiting_for_unban_user_id = State()
    waiting_for_archive_channel = State()
    waiting_for_main_group = State()
    waiting_for_edit_file_name = State()
    waiting_for_edit_lecture_name = State()
    waiting_for_admin_toggle_user_id = State()
    waiting_for_edit_video_title = State()
