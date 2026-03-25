"""Unit tests for the Registry class."""

import pytest

from src.app.registry import Registry


class TestRegistryInstantiation:
    """Tests for Registry instantiation."""

    def test_instantiation(self):
        """Test creating a Registry instance."""
        registry = Registry()
        assert registry is not None

    def test_instantiation_empty(self):
        """Test that Registry starts empty."""
        registry = Registry()
        items = list(registry.items())
        assert len(items) == 0


class TestRegistryRegister:
    """Tests for Registry.register method."""

    @pytest.fixture
    def registry(self):
        """Provide a fresh Registry instance."""
        return Registry()

    def test_register_single_item(self, registry):
        """Test registering a single item."""
        registry.register("key1", "value1")
        assert registry.get("key1") == "value1"

    def test_register_multiple_items(self, registry):
        """Test registering multiple items."""
        registry.register("key1", "value1")
        registry.register("key2", "value2")
        registry.register("key3", "value3")

        assert registry.get("key1") == "value1"
        assert registry.get("key2") == "value2"
        assert registry.get("key3") == "value3"

    def test_register_with_string_values(self, registry):
        """Test registering string values."""
        registry.register("name", "John")
        assert registry.get("name") == "John"

    def test_register_with_integer_values(self, registry):
        """Test registering integer values."""
        registry.register("count", 42)
        assert registry.get("count") == 42

    def test_register_with_list_values(self, registry):
        """Test registering list values."""
        items = [1, 2, 3]
        registry.register("items", items)
        assert registry.get("items") == items

    def test_register_with_dict_values(self, registry):
        """Test registering dictionary values."""
        data = {"key": "value", "number": 123}
        registry.register("data", data)
        assert registry.get("data") == data

    def test_register_with_object_values(self, registry):
        """Test registering object instances."""

        class CustomClass:
            def __init__(self, value):
                self.value = value

        obj = CustomClass(42)
        registry.register("object", obj)
        assert registry.get("object") is obj

    def test_register_with_none_value(self, registry):
        """Test registering None as a value."""
        registry.register("none_key", None)
        assert registry.get("none_key") is None

    def test_register_with_empty_string_key(self, registry):
        """Test that registering with empty string as key raises ValueError."""
        with pytest.raises(ValueError, match="Name must be a non-empty string"):
            registry.register("", "value")

    def test_register_with_special_characters_in_key(self, registry):
        """Test registering with special characters in key."""
        registry.register("key-with-dashes", "value1")
        registry.register("key_with_underscores", "value2")
        registry.register("key.with.dots", "value3")

        assert registry.get("key-with-dashes") == "value1"
        assert registry.get("key_with_underscores") == "value2"
        assert registry.get("key.with.dots") == "value3"

    def test_register_overwrites_existing_key(self, registry):
        """Test that registering with same key overwrites previous value."""
        registry.register("key", "value1")
        assert registry.get("key") == "value1"

        registry.register("key", "value2")
        assert registry.get("key") == "value2"

    def test_register_case_sensitive_keys(self, registry):
        """Test that keys are case-sensitive."""
        registry.register("Key", "value1")
        registry.register("key", "value2")
        registry.register("KEY", "value3")

        assert registry.get("Key") == "value1"
        assert registry.get("key") == "value2"
        assert registry.get("KEY") == "value3"


class TestRegistryGet:
    """Tests for Registry.get method."""

    @pytest.fixture
    def populated_registry(self):
        """Provide a Registry with some items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", 42)
        registry.register("item3", [1, 2, 3])
        return registry

    def test_get_existing_item(self, populated_registry):
        """Test getting an existing item."""
        assert populated_registry.get("item1") == "value1"
        assert populated_registry.get("item2") == 42
        assert populated_registry.get("item3") == [1, 2, 3]

    def test_get_non_existing_item_returns_none(self, populated_registry):
        """Test that getting non-existent item returns None."""
        assert populated_registry.get("non_existent") is None

    def test_get_after_unregister(self, populated_registry):
        """Test getting after unregistering an item."""
        populated_registry.unregister("item1")
        assert populated_registry.get("item1") is None

    def test_get_with_none_value(self):
        """Test getting an item with None value."""
        registry = Registry()
        registry.register("none_item", None)
        assert registry.get("none_item") is None

    def test_get_empty_registry_returns_none(self):
        """Test getting from empty registry returns None."""
        registry = Registry()
        assert registry.get("any_key") is None

    def test_get_is_idempotent(self, populated_registry):
        """Test that multiple gets return the same value."""
        value1 = populated_registry.get("item1")
        value2 = populated_registry.get("item1")
        value3 = populated_registry.get("item1")

        assert value1 == value2 == value3 == "value1"


class TestRegistryUnregister:
    """Tests for Registry.unregister method."""

    @pytest.fixture
    def populated_registry(self):
        """Provide a Registry with some items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")
        return registry

    def test_unregister_existing_item(self, populated_registry):
        """Test unregistering an existing item."""
        populated_registry.unregister("item1")
        assert populated_registry.get("item1") is None

    def test_unregister_makes_item_inaccessible(self, populated_registry):
        """Test that unregistered item becomes inaccessible."""
        assert populated_registry.get("item2") == "value2"
        populated_registry.unregister("item2")
        assert populated_registry.get("item2") is None

    def test_unregister_non_existing_item(self, populated_registry):
        """Test unregistering non-existent item doesn't raise error."""
        populated_registry.unregister("non_existent")  # Should not raise

    def test_unregister_from_empty_registry(self):
        """Test unregistering from empty registry doesn't raise error."""
        registry = Registry()
        registry.unregister("any_key")  # Should not raise

    def test_unregister_leaves_other_items_intact(self, populated_registry):
        """Test that unregistering one item leaves others intact."""
        populated_registry.unregister("item2")

        assert populated_registry.get("item1") == "value1"
        assert populated_registry.get("item2") is None
        assert populated_registry.get("item3") == "value3"

    def test_unregister_multiple_items(self, populated_registry):
        """Test unregistering multiple items."""
        populated_registry.unregister("item1")
        populated_registry.unregister("item2")

        assert populated_registry.get("item1") is None
        assert populated_registry.get("item2") is None
        assert populated_registry.get("item3") == "value3"

    def test_unregister_twice(self, populated_registry):
        """Test unregistering the same item twice."""
        populated_registry.unregister("item1")
        populated_registry.unregister("item1")  # Second unregister should be safe

        assert populated_registry.get("item1") is None

    def test_re_register_after_unregister(self, populated_registry):
        """Test re-registering an item after unregistering it."""
        populated_registry.unregister("item1")
        populated_registry.register("item1", "new_value")

        assert populated_registry.get("item1") == "new_value"


class TestRegistryClear:
    """Tests for Registry.clear method."""

    def test_clear_empty_registry(self):
        """Test clearing an empty registry."""
        registry = Registry()
        registry.clear()  # Should not raise

        assert registry.get("any_key") is None

    def test_clear_removes_all_items(self):
        """Test that clear removes all items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")

        registry.clear()

        assert registry.get("item1") is None
        assert registry.get("item2") is None
        assert registry.get("item3") is None

    def test_clear_then_register(self):
        """Test that we can register after clearing."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.clear()
        registry.register("item2", "value2")

        assert registry.get("item1") is None
        assert registry.get("item2") == "value2"

    def test_clear_items_count_to_zero(self):
        """Test that items count becomes zero after clear."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.clear()
        items = list(registry.items())

        assert len(items) == 0

    def test_multiple_clears(self):
        """Test multiple clear operations."""
        registry = Registry()
        registry.register("item1", "value1")

        registry.clear()
        registry.clear()
        registry.clear()

        assert registry.get("item1") is None


class TestRegistryItems:
    """Tests for Registry.items method."""

    def test_items_empty_registry(self):
        """Test items from empty registry."""
        registry = Registry()
        items = list(registry.items())

        assert len(items) == 0

    def test_items_returns_generator(self):
        """Test that items returns a generator."""
        registry = Registry()
        registry.register("item1", "value1")

        items = registry.items()
        from collections.abc import Generator

        assert isinstance(items, Generator)

    def test_items_single_item(self):
        """Test items with single registered item."""
        registry = Registry()
        registry.register("item1", "value1")

        items = list(registry.items())

        assert len(items) == 1
        assert items[0] == ("item1", "value1")

    def test_items_multiple_items(self):
        """Test items with multiple registered items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")

        items = list(registry.items())

        assert len(items) == 3
        assert ("item1", "value1") in items
        assert ("item2", "value2") in items
        assert ("item3", "value3") in items

    def test_items_contains_tuples(self):
        """Test that items are returned as (name, object) tuples."""
        registry = Registry()
        registry.register("name", "John")

        items = list(registry.items())

        assert len(items) == 1
        name, obj = items[0]
        assert name == "name"
        assert obj == "John"

    def test_items_after_unregister(self):
        """Test items after unregistering."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.unregister("item1")

        items = list(registry.items())
        assert len(items) == 1
        assert items[0] == ("item2", "value2")

    def test_items_after_clear(self):
        """Test items after clear."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.clear()

        items = list(registry.items())
        assert len(items) == 0

    def test_items_can_iterate_multiple_times(self):
        """Test that we can iterate items multiple times."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        items1 = list(registry.items())
        items2 = list(registry.items())

        assert len(items1) == len(items2) == 2

    def test_items_unpacking(self):
        """Test unpacking items."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        for name, obj in registry.items():
            assert isinstance(name, str)
            assert isinstance(obj, str)


class TestRegistryGeneric:
    """Tests for Registry with generic types."""

    def test_registry_with_string_values(self):
        """Test Registry with string values."""
        registry = Registry[str]()
        registry.register("greeting", "Hello")
        registry.register("farewell", "Goodbye")

        assert registry.get("greeting") == "Hello"
        assert registry.get("farewell") == "Goodbye"

    def test_registry_with_integer_values(self):
        """Test Registry with integer values."""
        registry = Registry[int]()
        registry.register("count", 42)
        registry.register("answer", 101)

        assert registry.get("count") == 42
        assert registry.get("answer") == 101

    def test_registry_with_list_values(self):
        """Test Registry with list values."""
        registry = Registry[list]()
        registry.register("numbers", [1, 2, 3])
        registry.register("letters", ["a", "b", "c"])

        assert registry.get("numbers") == [1, 2, 3]
        assert registry.get("letters") == ["a", "b", "c"]

    def test_registry_with_custom_objects(self):
        """Test Registry with custom objects."""

        class Service:
            def __init__(self, name):
                self.name = name

        registry = Registry[Service]()
        service1 = Service("Service1")
        service2 = Service("Service2")

        registry.register("service1", service1)
        registry.register("service2", service2)

        assert registry.get("service1") is service1
        s1 = registry.get("service1")
        assert s1 is not None
        assert s1.name == "Service1"
        assert registry.get("service2") is service2


class TestRegistryWorkflow:
    """Tests for typical Registry workflows."""

    def test_service_registry_workflow(self):
        """Test a typical service registry workflow."""

        class DatabaseService:
            def query(self):
                return "database result"

        class CacheService:
            def get(self):
                return "cached value"

        registry = Registry()

        db_service = DatabaseService()
        cache_service = CacheService()

        registry.register("database", db_service)
        registry.register("cache", cache_service)

        assert registry.get("database") is db_service
        assert registry.get("cache") is cache_service
        db = registry.get("database")
        assert db is not None
        assert db.query() == "database result"
        cache = registry.get("cache")
        assert cache is not None
        assert cache.get() == "cached value"

    def test_plugin_registry_workflow(self):
        """Test a typical plugin registry workflow."""
        plugins = Registry()

        plugins.register("plugin_a", {"name": "Plugin A", "version": "1.0"})
        plugins.register("plugin_b", {"name": "Plugin B", "version": "2.0"})

        all_plugins = list(plugins.items())
        assert len(all_plugins) == 2

        plugins.unregister("plugin_a")
        remaining = list(plugins.items())
        assert len(remaining) == 1

    def test_factory_registry_workflow(self):
        """Test a typical factory registry workflow."""

        def string_factory():
            return "string"

        def list_factory():
            return []

        def dict_factory():
            return {}

        registry = Registry()

        registry.register("string", string_factory)
        registry.register("list", list_factory)
        registry.register("dict", dict_factory)

        string_factory_fn = registry.get("string")
        assert string_factory_fn is not None
        assert string_factory_fn() == "string"

        list_factory_fn = registry.get("list")
        assert list_factory_fn is not None
        assert list_factory_fn() == []

        dict_factory_fn = registry.get("dict")
        assert dict_factory_fn is not None
        assert dict_factory_fn() == {}

    def test_concurrent_registration(self):
        """Test registering and retrieving in sequence."""
        registry = Registry()

        for i in range(100):
            registry.register(f"item_{i}", i)

        for i in range(100):
            assert registry.get(f"item_{i}") == i

    def test_large_registry(self):
        """Test Registry with many items."""
        registry = Registry()

        # Register many items
        for i in range(1000):
            registry.register(f"key_{i}", f"value_{i}")

        # Verify all items
        assert len(list(registry.items())) == 1000
        assert registry.get("key_500") == "value_500"

        # Clear and verify empty
        registry.clear()
        assert len(list(registry.items())) == 0


class TestRegistryEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_register_with_mutable_value(self):
        """Test registering a mutable value."""
        registry = Registry()
        mutable_list = [1, 2, 3]

        registry.register("list", mutable_list)

        retrieved = registry.get("list")
        assert retrieved is mutable_list

        # Modify the retrieved list
        assert retrieved is not None
        retrieved.append(4)
        assert registry.get("list") == [1, 2, 3, 4]

    def test_register_with_boolean_values(self):
        """Test registering boolean values."""
        registry = Registry()

        registry.register("true_key", True)
        registry.register("false_key", False)

        assert registry.get("true_key") is True
        assert registry.get("false_key") is False

    def test_register_with_zero_value(self):
        """Test registering zero as a value."""
        registry = Registry()
        registry.register("zero", 0)

        assert registry.get("zero") == 0
        assert registry.get("zero") is not None

    def test_register_with_empty_string_value(self):
        """Test registering empty string as a value."""
        registry = Registry()
        registry.register("empty", "")

        assert registry.get("empty") == ""
        assert registry.get("empty") is not None

    def test_register_with_empty_list_value(self):
        """Test registering empty list as a value."""
        registry = Registry()
        registry.register("empty_list", [])

        assert registry.get("empty_list") == []
        assert registry.get("empty_list") is not None

    def test_register_with_empty_dict_value(self):
        """Test registering empty dict as a value."""
        registry = Registry()
        registry.register("empty_dict", {})

        assert registry.get("empty_dict") == {}
        assert registry.get("empty_dict") is not None

    def test_whitespace_keys(self):
        """Test keys with whitespace."""
        registry = Registry()

        registry.register(" key with spaces ", "value1")
        registry.register("\tkey\twith\ttabs\t", "value2")

        assert registry.get(" key with spaces ") == "value1"
        assert registry.get("\tkey\twith\ttabs\t") == "value2"


class TestRegistryImmutability:
    """Tests for Registry immutability (frozen dataclass)."""

    def test_registry_is_frozen(self):
        """Test that Registry is frozen and cannot be modified."""
        registry = Registry()

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            registry.new_attribute = "test"  # type: ignore

    def test_cannot_reassign_registry_field(self):
        """Test that registry field cannot be reassigned."""
        registry = Registry()

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            registry._registry = {}  # type: ignore

    def test_frozen_prevents_attribute_addition(self):
        """Test that frozen dataclass prevents adding new attributes."""
        registry = Registry()
        registry.register("key", "value")

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            registry.extra = "something"  # type: ignore

    def test_methods_modify_internal_state(self):
        """Test that methods can modify internal frozen state."""
        registry = Registry()

        # Methods should work despite being frozen
        registry.register("key", "value")
        assert registry.get("key") == "value"

        registry.unregister("key")
        assert registry.get("key") is None

        registry.clear()
        assert len(list(registry.items())) == 0


class TestRegistryRepresentation:
    """Tests for Registry string representation."""

    def test_repr_does_not_include_registry_field(self):
        """Test that repr doesn't include registry field (repr=False)."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        repr_str = repr(registry)

        # repr should have class name but not include registry field
        assert "Registry" in repr_str
        assert "registry=" not in repr_str

    def test_repr_is_not_empty(self):
        """Test that registry has a repr."""
        registry = Registry()
        repr_str = repr(registry)

        assert len(repr_str) > 0
        assert isinstance(repr_str, str)


class TestRegistryContains:
    """Tests for checking if a key is registered."""

    def test_check_key_existence_via_get(self):
        """Test checking key existence by comparing get result to None."""
        registry = Registry()
        registry.register("existing", "value")

        # Method to check existence
        assert registry.get("existing") is not None
        assert registry.get("non_existing") is None

    def test_key_not_in_registry_initially(self):
        """Test that new key is not in registry initially."""
        registry = Registry()

        assert registry.get("new_key") is None

    def test_multiple_keys_independent_existence(self):
        """Test that each key's existence is independent."""
        registry = Registry()
        registry.register("key1", "value1")

        assert registry.get("key1") is not None
        assert registry.get("key2") is None
        assert registry.get("key3") is None


class TestRegistrySize:
    """Tests for determining registry size."""

    def test_items_count_empty_registry(self):
        """Test counting items in empty registry."""
        registry = Registry()
        count = len(list(registry.items()))

        assert count == 0

    def test_items_count_after_register(self):
        """Test counting items after registration."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        count = len(list(registry.items()))
        assert count == 2

    def test_items_count_after_unregister(self):
        """Test counting items after unregistering."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")
        registry.register("key3", "value3")

        registry.unregister("key2")

        count = len(list(registry.items()))
        assert count == 2

    def test_items_count_after_clear(self):
        """Test counting items after clear."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        registry.clear()

        count = len(list(registry.items()))
        assert count == 0


class TestRegistryCallables:
    """Tests for registering callable objects."""

    def test_register_function(self):
        """Test registering a function."""

        def my_function():
            return "result"

        registry = Registry()
        registry.register("func", my_function)

        retrieved = registry.get("func")
        assert retrieved is not None
        assert retrieved is my_function
        assert retrieved() == "result"

    def test_register_lambda(self):
        """Test registering a lambda function."""
        registry = Registry()

        def my_lambda(x):
            return x * 2

        registry.register("double", my_lambda)

        retrieved = registry.get("double")
        assert retrieved is not None
        assert retrieved is my_lambda
        assert retrieved(5) == 10

    def test_register_class(self):
        """Test registering a class (not instance)."""

        class MyClass:
            attr = "class_attr"

        registry = Registry()
        registry.register("MyClass", MyClass)

        retrieved = registry.get("MyClass")
        assert retrieved is MyClass
        assert retrieved.attr == "class_attr"

    def test_register_builtin_function(self):
        """Test registering built-in functions."""
        registry = Registry()
        registry.register("len", len)
        registry.register("str", str)

        assert registry.get("len") is len
        assert registry.get("str") is str

    def test_callable_not_invoked_on_register(self):
        """Test that registering a callable doesn't invoke it."""
        call_count = [0]

        def tracked_function():
            call_count[0] += 1
            return "result"

        registry = Registry()
        registry.register("func", tracked_function)

        # Function should not be called during registration
        assert call_count[0] == 0

        # Only call when explicitly invoked
        func = registry.get("func")
        assert func is not None
        func()
        assert call_count[0] == 1

    def test_register_method(self):
        """Test registering methods."""

        class MyClass:
            def my_method(self):
                return "method_result"

        instance = MyClass()
        registry = Registry()

        registry.register("method", instance.my_method)

        retrieved = registry.get("method")
        assert callable(retrieved)
        assert retrieved() == "method_result"


class TestRegistryTypes:
    """Tests for various type registrations."""

    def test_register_tuple(self):
        """Test registering tuple values."""
        registry = Registry()
        my_tuple = (1, 2, 3)

        registry.register("tuple", my_tuple)

        assert registry.get("tuple") == my_tuple

    def test_register_set(self):
        """Test registering set values."""
        registry = Registry()
        my_set = {1, 2, 3}

        registry.register("set", my_set)

        assert registry.get("set") == my_set

    def test_register_custom_object(self):
        """Test registering custom objects."""

        class CustomObject:
            def __init__(self, value):
                self.value = value

        obj = CustomObject(42)
        registry = Registry()

        registry.register("obj", obj)

        retrieved = registry.get("obj")
        assert retrieved is not None
        assert retrieved is obj
        assert retrieved.value == 42

    def test_register_nested_container(self):
        """Test registering nested containers."""
        registry = Registry()
        nested = {"list": [1, 2, 3], "dict": {"a": 1}, "tuple": (4, 5)}

        registry.register("nested", nested)

        retrieved = registry.get("nested")
        assert retrieved is not None
        assert retrieved == nested
        assert retrieved["list"] == [1, 2, 3]

    def test_register_exception_class(self):
        """Test registering exception classes."""
        registry = Registry()

        registry.register("ValueError", ValueError)
        registry.register("TypeError", TypeError)

        assert registry.get("ValueError") is ValueError
        assert registry.get("TypeError") is TypeError


class TestRegistryInitialization:
    """Tests for Registry initialization."""

    def test_registry_field_cannot_be_passed_as_init_parameter(self):
        """Test that registry field cannot be initialized via __init__."""
        # Registry should have init=False for the registry field
        # This test verifies that even if we try, it will fail

        try:
            # This should fail because registry is init=False
            registry = Registry(_registry={"key": "value"})  # type: ignore
            # If it doesn't raise, the field should still be empty
            # (Python 3.13+ allows this syntax but ignores the parameter)
            assert list(registry.items()) == []
        except TypeError:
            # Expected if init=False is properly enforced
            pass

    def test_registry_starts_with_empty_dict(self):
        """Test that registry starts as empty dict."""
        registry = Registry()
        items = list(registry.items())

        assert items == []

    def test_registry_uses_default_factory(self):
        """Test that registry field uses default_factory."""
        registry1 = Registry()
        registry2 = Registry()

        # Each should have its own dict instance
        registry1.register("key", "value")

        assert registry1.get("key") == "value"
        assert registry2.get("key") is None


class TestRegistryEquality:
    """Tests for Registry comparison and equality."""

    def test_registry_instances_are_different(self):
        """Test that Registry instances are different objects."""
        registry1 = Registry()
        registry2 = Registry()

        assert registry1 is not registry2

    def test_registry_equality_with_same_items(self):
        """Test equality of registries with same items."""
        registry1 = Registry()
        registry1.register("key1", "value1")

        registry2 = Registry()
        registry2.register("key1", "value1")

        # By default, dataclass instances compare by value
        # But registries with same items might not be equal due to
        # different object identities
        assert list(registry1.items()) == list(registry2.items())

    def test_registry_identity_unchanged_after_modification(self):
        """Test that registry identity remains same after modifications."""
        registry = Registry()
        id1 = id(registry)

        registry.register("key", "value")
        id2 = id(registry)

        assert id1 == id2

    def test_registry_internal_dict_identity(self):
        """Test that internal dict remains the same object."""
        registry = Registry()

        dict1 = registry._registry
        registry.register("key", "value")
        dict2 = registry._registry

        # Same internal dict object
        assert dict1 is dict2


class TestRegistryIterationBehavior:
    """Tests for iteration and generator behavior."""

    def test_items_generator_not_materialized(self):
        """Test that items returns a generator, not a list."""
        registry = Registry()
        registry.register("key1", "value1")

        gen = registry.items()

        # Should be a generator
        from collections.abc import Generator

        assert isinstance(gen, Generator)

    def test_items_generator_consumed_once(self):
        """Test that generator must be consumed."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        gen = registry.items()

        # First iteration
        list1 = list(gen)
        assert len(list1) == 2

        # Generator is exhausted
        list2 = list(gen)
        assert len(list2) == 0

    def test_fresh_generator_each_call(self):
        """Test that each items() call returns a fresh generator."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        list1 = list(registry.items())
        list2 = list(registry.items())

        assert len(list1) == 2
        assert len(list2) == 2

    def test_items_yields_correct_types(self):
        """Test that items yields tuples of (str, object)."""
        registry = Registry()
        registry.register("key", "value")

        for name, obj in registry.items():
            assert isinstance(name, str)
            assert obj == "value"


class TestRegistrySequentialOperations:
    """Tests for sequential and dependent operations."""

    def test_register_get_unregister_cycle(self):
        """Test register -> get -> unregister cycle."""
        registry = Registry()

        # Register
        registry.register("key", "value")
        assert registry.get("key") == "value"

        # Unregister
        registry.unregister("key")
        assert registry.get("key") is None

        # Re-register
        registry.register("key", "new_value")
        assert registry.get("key") == "new_value"

    def test_register_overwrite_sequence(self):
        """Test multiple overwrites in sequence."""
        registry = Registry()

        values = ["v1", "v2", "v3", "v4", "v5"]

        for value in values:
            registry.register("key", value)
            assert registry.get("key") == value

    def test_clear_then_full_workflow(self):
        """Test clear followed by full workflow."""
        registry = Registry()

        # Initial registration
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        # Clear everything
        registry.clear()

        # Full new workflow
        registry.register("key3", "value3")
        registry.register("key4", "value4")

        assert registry.get("key1") is None
        assert registry.get("key2") is None
        assert registry.get("key3") == "value3"
        assert registry.get("key4") == "value4"

    def test_alternating_register_unregister(self):
        """Test alternating register and unregister operations."""
        registry = Registry()

        registry.register("key1", "value1")
        assert registry.get("key1") == "value1"

        registry.register("key2", "value2")
        assert registry.get("key2") == "value2"

        registry.unregister("key1")
        assert registry.get("key1") is None
        assert registry.get("key2") == "value2"

        registry.unregister("key2")
        assert registry.get("key2") is None


class TestRegistryKeyHandling:
    """Tests for special key handling scenarios."""

    def test_unicode_keys(self):
        """Test registering with Unicode keys."""
        registry = Registry()

        registry.register("日本語", "Japanese")
        registry.register("中文", "Chinese")
        registry.register("한글", "Korean")

        assert registry.get("日本語") == "Japanese"
        assert registry.get("中文") == "Chinese"
        assert registry.get("한글") == "Korean"

    def test_very_long_keys(self):
        """Test keys with very long strings."""
        registry = Registry()
        long_key = "k" * 10000

        registry.register(long_key, "value")

        assert registry.get(long_key) == "value"

    def test_numeric_string_keys(self):
        """Test numeric strings as keys (not integers)."""
        registry = Registry()

        registry.register("123", "numeric string key")
        registry.register("456", "another numeric key")

        assert registry.get("123") == "numeric string key"
        assert registry.get("456") == "another numeric key"

    def test_key_with_special_characters(self):
        """Test keys with various special characters."""
        registry = Registry()

        special_keys = [
            "key!@#$%^&*()",
            "key[with]brackets",
            "key{with}braces",
            "key<with>angles",
            "key|with|pipes",
            "key:with:colons",
            "key;with;semicolons",
        ]

        for key in special_keys:
            registry.register(key, f"value_for_{key}")

        for key in special_keys:
            assert registry.get(key) == f"value_for_{key}"


class TestRegistryDataPersistence:
    """Tests for data persistence and integrity."""

    def test_registered_value_not_modified(self):
        """Test that registered values are not modified by registry."""
        registry = Registry()
        original = {"a": 1, "b": 2}

        registry.register("dict", original)

        retrieved = registry.get("dict")
        assert retrieved == original
        assert retrieved is original

    def test_multiple_references_to_same_object(self):
        """Test registering same object with different names."""
        registry = Registry()
        obj = object()

        registry.register("name1", obj)
        registry.register("name2", obj)

        assert registry.get("name1") is registry.get("name2")
        assert registry.get("name1") is obj

    def test_value_identity_preserved(self):
        """Test that value identity is preserved through registry."""
        registry = Registry()

        class TrackedObject:
            pass

        obj = TrackedObject()
        registry.register("tracked", obj)

        retrieved = registry.get("tracked")

        assert retrieved is obj
        assert id(retrieved) == id(obj)


class TestFactoryFunctionsSingleton:
    """Tests for singleton factory functions with @cache decorator."""

    def test_get_workflow_services_returns_registry(self):
        """Test that get_workflow_services returns a Registry instance."""
        from src.app.registry import get_workflow_services

        registry = get_workflow_services()
        assert isinstance(registry, Registry)

    def test_get_workflow_services_returns_same_instance(self):
        """Test that get_workflow_services returns the same instance (singleton)."""
        from src.app.registry import get_workflow_services

        first_call = get_workflow_services()
        second_call = get_workflow_services()
        third_call = get_workflow_services()

        assert first_call is second_call
        assert second_call is third_call
        assert id(first_call) == id(second_call) == id(third_call)

    def test_get_workflow_services_works_as_registry(self):
        """Test that get_workflow_services registry can register and retrieve items."""
        from unittest.mock import Mock

        from src.app.registry import get_workflow_services

        registry = get_workflow_services()
        registry.clear()  # Clear any previous state

        # Create a mock IWorkflowService
        mock_service = Mock()
        mock_service.create_batch_pdf = Mock(return_value=[])

        registry.register("test_service", mock_service)
        assert registry.get("test_service") is mock_service

    def test_get_artwork_services_returns_singleton(self):
        """Test that get_artwork_services returns the same instance."""
        from src.app.registry import get_artwork_services

        first = get_artwork_services()
        second = get_artwork_services()

        assert first is second

    def test_get_order_services_returns_singleton(self):
        """Test that get_order_services returns the same instance."""
        from src.app.registry import get_order_services

        first = get_order_services()
        second = get_order_services()

        assert first is second

    def test_get_sale_services_returns_singleton(self):
        """Test that get_sale_services returns the same instance."""
        from src.app.registry import get_sale_services

        first = get_sale_services()
        second = get_sale_services()

        assert first is second

    def test_get_stock_services_returns_singleton(self):
        """Test that get_stock_services returns the same instance."""
        from src.app.registry import get_stock_services

        first = get_stock_services()
        second = get_stock_services()

        assert first is second

    def test_get_use_cases_returns_singleton(self):
        """Test that get_use_cases returns the same instance."""
        from src.app.registry import get_use_cases

        first = get_use_cases()
        second = get_use_cases()

        assert first is second

    def test_factory_functions_return_different_instances(self):
        """Test that different factory functions return different instances."""
        from src.app.registry import (
            get_artwork_services,
            get_order_services,
            get_sale_services,
            get_stock_services,
            get_use_cases,
            get_workflow_services,
        )

        artwork = get_artwork_services()
        order = get_order_services()
        sale = get_sale_services()
        stock = get_stock_services()
        workflow = get_workflow_services()
        use_cases = get_use_cases()

        # All should be different instances
        instances = [artwork, order, sale, stock, workflow, use_cases]
        assert len({id(inst) for inst in instances}) == 6

    def test_workflow_services_persists_data_across_calls(self):
        """Test that data persists in workflow_services across multiple get calls."""
        from unittest.mock import Mock

        from src.app.registry import get_workflow_services

        # Get first instance and register data
        registry1 = get_workflow_services()
        registry1.clear()

        mock_service = Mock()
        registry1.register("persistent_key", mock_service)

        # Get second instance and verify data is still there
        registry2 = get_workflow_services()
        assert registry2.get("persistent_key") is mock_service

        # Since they're the same instance, this should be true
        assert registry1 is registry2

    def test_multiple_registrations_in_singleton(self):
        """Test multiple registrations in singleton workflow_services."""
        from unittest.mock import Mock

        from src.app.registry import get_workflow_services

        registry = get_workflow_services()
        registry.clear()

        service1 = Mock(name="service1")
        service2 = Mock(name="service2")
        service3 = Mock(name="service3")

        registry.register("service1", service1)
        registry.register("service2", service2)
        registry.register("service3", service3)

        assert registry.get("service1") is service1
        assert registry.get("service2") is service2
        assert registry.get("service3") is service3

    def test_clear_in_singleton_affects_subsequent_calls(self):
        """Test that clear in singleton affects subsequent get calls."""
        from unittest.mock import Mock

        from src.app.registry import get_workflow_services

        registry = get_workflow_services()
        registry.clear()

        mock_service = Mock()
        registry.register("test_item", mock_service)

        assert registry.get("test_item") is mock_service

        registry.clear()

        # Get another reference - should be empty
        registry2 = get_workflow_services()
        assert registry2.get("test_item") is None

    def test_cache_decorator_is_applied(self):
        """Test that @cache decorator is applied by checking the wrapper."""
        from src.app.registry import get_workflow_services

        # The function should be wrapped by functools.cache
        # Calling it multiple times should not create new instances
        instance1 = get_workflow_services()
        instance2 = get_workflow_services()

        # If cache is properly applied, these are the same object
        assert instance1 is instance2
        assert instance1.__class__.__name__ == "Registry"

    def test_all_factory_functions_are_callable(self):
        """Test that all factory functions are callable."""
        from src.app.registry import (
            get_artwork_services,
            get_order_services,
            get_sale_services,
            get_stock_services,
            get_use_cases,
            get_workflow_services,
        )

        functions = [
            get_artwork_services,
            get_order_services,
            get_sale_services,
            get_stock_services,
            get_workflow_services,
            get_use_cases,
        ]

        for func in functions:
            assert callable(func)
            result = func()
            assert isinstance(result, Registry)

    def test_workflow_services_concurrent_access_singleton(self):
        """Test that concurrent access to workflow_services returns same instance."""
        import threading

        from src.app.registry import get_workflow_services

        instances = []
        lock = threading.Lock()

        def get_and_store():
            instance = get_workflow_services()
            with lock:
                instances.append(instance)

        threads = [threading.Thread(target=get_and_store) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(instances) == 10
        assert all(inst is instances[0] for inst in instances)

    def test_workflow_services_register_and_unregister_in_singleton(self):
        """Test register and unregister operations in singleton workflow_services."""
        from unittest.mock import Mock

        from src.app.registry import get_workflow_services

        registry = get_workflow_services()
        registry.clear()

        mock_service = Mock()
        registry.register("temp_service", mock_service)
        assert registry.get("temp_service") is mock_service

        registry.unregister("temp_service")
        assert registry.get("temp_service") is None

        # Verify same instance
        registry2 = get_workflow_services()
        assert registry2.get("temp_service") is None
        assert registry2 is registry
